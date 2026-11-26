import asyncio
import json
import re
from datetime import date
from uuid import NAMESPACE_URL, uuid4, uuid5

from pydantic import ValidationError

from p1_core_backend.agent.prompts import build_system_prompt
from p1_core_backend.db import store
from p1_core_backend.mcp_client.hub import McpHub
from shared.ids import FORM_TEMPLATES
from shared.llm import LlmUnavailable, chat_with_tools, is_mock
from shared.schemas import ActionPlan, LifeEvent, Notification, PrefilledForm


UNVERIFIED_REPLY = (
    "I can only answer from verified official data, and I don't have that one."
)

MOVE_PATTERN = re.compile(
    r"\b(?:mov(?:e|es|ed|ing)|shift(?:s|ed|ing)?|"
    r"relocat(?:e|es|ed|ing|ion)|transfer(?:s|red|ring)?)\b"
)

PLACE_STATES = {
    "bengaluru": "karnataka",
    "bangalore": "karnataka",
    "mysuru": "karnataka",
    "karnataka": "karnataka",
    "pune": "maharashtra",
    "mumbai": "maharashtra",
    "maharashtra": "maharashtra",
}
PLACE_PATTERN = re.compile(r"\b(" + "|".join(PLACE_STATES) + r")\b")


def _relocation(message: str, current_state: str) -> LifeEvent | None:
    text = message.casefold()
    move = MOVE_PATTERN.search(text)
    if not move:
        return None

    # Start at the movement phrase so "born in Bengaluru" doesn't
    # get mistaken for the destination in Ravi's demo question.
    places = PLACE_PATTERN.findall(text[move.end():])
    if not places:
        return None

    destination = PLACE_STATES[places[-1]]
    return LifeEvent(
        event_type=(
            "relocation_intrastate"
            if destination == current_state
            else "relocation_interstate"
        ),
        from_state=current_state,
        to_state=destination,
    )


def _context_for(user_id: str, context_id: str | None) -> str:
    if not context_id:
        return ""

    notification = store.get_notification(context_id)
    if notification:
        if notification.user_id != user_id or not notification.context_id:
            return ""
        context_id = notification.context_id

    form = store.get_form(context_id)
    if form and form.user_id == user_id:
        return f"A {form.service_id} form is ready for review."

    for notice in store.list_notifications(user_id):
        if notice.open_target == "chat" and notice.context_id == context_id:
            info = store.get_extracted(context_id)
            if info:
                context = f"From your notification: {info.summary}."
                if info.due_date:
                    context += f" Reported due date: {info.due_date.isoformat()}."
                return context

    return ""


async def _scripted_reply(
    hub: McpHub,
    profile,
    message: str,
    conversation_id: str,
) -> tuple[str, ActionPlan | None]:
    event = _relocation(message, profile.current_state)
    if event:
        # Step 6 supplies this module.
        from p1_core_backend.agent.plan_builder import build_plan

        plan = await build_plan(hub, profile, event, conversation_id)
        if plan.items:
            return plan.summary, plan
        return UNVERIFIED_REPLY, None

    text = message.casefold()
    service_id = None
    if "life certificate" in text or "jeevan pramaan" in text:
        service_id = "pension_life_certificate"
    elif re.search(r"\b(?:licen[cs]e|dl)\b", text) and re.search(
        r"\b(?:renew\w*|expir\w*)\b", text
    ):
        service_id = "dl_renewal"
    elif "voter" in text:
        service_id = "voter_shift"

    if service_id is None:
        return UNVERIFIED_REPLY, None

    result = await hub.call(
        "services",
        "get_process",
        {"service_id": service_id, "state": profile.current_state},
        conversation_id,
    )
    data = result.data if isinstance(result.data, dict) else {}
    if not (result.ok and data.get("steps")):
        return UNVERIFIED_REPLY, None

    verified = data.get("verified") and result.sources and not result.simulated
    label = "" if verified else "Unverified guidance. "
    return label + " ".join(data["steps"]), None


async def _live_reply(hub: McpHub, profile, message: str, context: str, cid: str):
    tools = hub.llm_tools()
    allowed = {entry["function"]["name"] for entry in tools}

    # Give the model only the profile details needed for civic guidance.
    profile_context = {
        "language": profile.language,
        "current_state": profile.current_state,
        "birth_state": profile.birth_state,
        "documents": [
            {"doc_id": doc.doc_id, "expiry_date": doc.expiry_date}
            for doc in profile.documents
        ],
    }
    messages = [
        {"role": "system", "content": build_system_prompt(profile.language)},
        {
            "role": "user",
            "content": json.dumps(
                {"profile": profile_context, "opened_from": context, "question": message},
                default=str,
            ),
        },
    ]

    for _ in range(8):
        assistant = await asyncio.to_thread(chat_with_tools, messages, tools)
        calls = assistant.get("tool_calls") or []
        if not calls:
            content = assistant.get("content")
            if not isinstance(content, str) or not content.strip():
                raise LlmUnavailable("The model returned an empty reply")
            return content

        messages.append(assistant)
        for call in calls:
            function = call["function"]
            name = function["name"]
            try:
                args = json.loads(function["arguments"])
            except (TypeError, ValueError):
                args = None

            if name not in allowed or not isinstance(args, dict):
                payload = json.dumps({"ok": False, "error": "Invalid tool call"})
            else:
                # Strip model-supplied identity fields and put back only
                # the fields the selected tool actually accepts.
                for field in ("user_id", "held", "profile"):
                    args.pop(field, None)
                if name == "deadlines__list_upcoming":
                    args["user_id"] = profile.user_id
                if name == "documents__get_affected_documents":
                    args["held"] = [
                        doc.model_dump(mode="json") for doc in profile.documents
                    ]

                server, tool = name.split("__", 1)
                result = await hub.call(server, tool, args, cid)
                payload = result.model_dump_json()

            messages.append(
                {"role": "tool", "tool_call_id": call["id"], "content": payload}
            )

    raise LlmUnavailable("The model reached the tool-call limit")


async def _prepare_voter_form(hub, profile, plan, event, conversation_id):
    if "voter_shift" not in FORM_TEMPLATES:
        return
    if not any(item.service_id == "voter_shift" for item in plan.items):
        return

    key = uuid5(NAMESPACE_URL, f"civicsaathi:{profile.user_id}:voter_shift").hex
    if store.get_notification(key):
        return

    result = await hub.call(
        "formfill",
        "prefill_form",
        {
            "service_id": "voter_shift",
            "state": event.to_state or profile.current_state,
            "profile": profile.model_dump(mode="json"),
        },
        conversation_id,
    )
    if not result.ok:
        return

    try:
        form = PrefilledForm.model_validate(result.data)
    except ValidationError:
        return

    if form.service_id != "voter_shift":
        return

    # Stable IDs keep repeated requests from creating extra saved forms
    # or notifications for the same user and service.
    form = form.model_copy(
        update={
            "form_id": f"voter-{key}",
            "user_id": profile.user_id,
            "state": event.to_state or profile.current_state,
        }
    )
    store.save_form(form)
    store.save_notification(
        Notification(
            notification_id=key,
            user_id=profile.user_id,
            title="Voter-shift form is ready to review",
            body="Open the draft to review and complete your form.",
            type="form_ready",
            open_target="form",
            context_id=form.form_id,
            created_at=date.today().isoformat() + "T00:00:00",
        )
    )


async def run_chat(
    user_id: str,
    message: str,
    context_id: str | None = None,
    *,
    hub: McpHub,
) -> tuple[str, ActionPlan | None, str]:
    conversation_id = uuid4().hex
    profile = store.get_profile(user_id)
    if profile is None:
        return "I couldn't find that profile.", None, conversation_id

    store.save_conversation(conversation_id, user_id)
    context = _context_for(user_id, context_id)
    question = f"{message}\n{context}" if context else message
    event = _relocation(message, profile.current_state)

    if event or is_mock():
        reply, plan = await _scripted_reply(
            hub, profile, question, conversation_id
        )
    else:
        try:
            reply = await _live_reply(hub, profile, message, context, conversation_id)
            plan = None
        except LlmUnavailable:
            reply, plan = await _scripted_reply(
                hub, profile, question, conversation_id
            )

    if plan and event:
        await _prepare_voter_form(hub, profile, plan, event, conversation_id)
    if context and is_mock():
        reply = f"{context}\n\n{reply}"

    return reply, plan, conversation_id