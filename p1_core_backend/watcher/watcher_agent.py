import asyncio
import re
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError

from p1_core_backend.db import store
from p1_core_backend.mcp_client.hub import McpHub
from p4_voice_notify.push.fcm import send_push
from shared.ids import DOC_IDS, FORM_TEMPLATES, SERVICE_IDS
from shared.schemas import (
    ExtractedInfo,
    IncomingMessage,
    Notification,
    PrefilledForm,
    Reminder,
    UserProfile,
)


OTP_PATTERN = re.compile(
    r"\b(?:otp|one[- ]time (?:password|code|passcode)|verification code)\b",
    re.IGNORECASE,
)
MESSAGE_LOCK = asyncio.Lock()


def _stable_id(*parts: str) -> str:
    return uuid5(NAMESPACE_URL, ":".join(("civicsaathi", *parts))).hex


def _save_notice(notice: Notification) -> None:
    if store.get_notification(notice.notification_id):
        return
    store.save_notification(notice)
    send_push(notice.model_dump(mode="json"))


async def _create_reminder(
    hub: McpHub,
    profile: UserProfile,
    info: ExtractedInfo,
) -> bool:
    if info.due_date is None:
        return True

    if info.service_id:
        await hub.call(
            "services",
            "get_process",
            {"service_id": info.service_id, "state": profile.current_state},
        )

    reminder = Reminder(
        reminder_id=_stable_id(profile.user_id, info.message_id, "reminder"),
        user_id=profile.user_id,
        doc_id=info.doc_id,
        title=info.summary,
        due_date=info.due_date,
        source_message_id=info.message_id,
    )
    result = await hub.call(
        "deadlines", "add_reminder", {"reminder": reminder.model_dump(mode="json")}
    )
    if not result.ok:
        return False

    _save_notice(
        Notification(
            notification_id=reminder.reminder_id,
            user_id=profile.user_id,
            title=reminder.title,
            body=f"Due date: {info.due_date.isoformat()}",
            type="reminder",
            open_target="chat",
            context_id=info.message_id,
            created_at=datetime.now(timezone.utc),
        )
    )
    return True


async def _prepare_form(
    hub: McpHub,
    profile: UserProfile,
    service_id: str,
) -> bool:
    # Same ID as the chat flow, so both paths share one draft notification.
    notification_id = _stable_id(profile.user_id, service_id)
    if store.get_notification(notification_id):
        return True

    result = await hub.call(
        "formfill",
        "prefill_form",
        {
            "service_id": service_id,
            "state": profile.current_state,
            "profile": profile.model_dump(mode="json"),
        },
    )
    if not result.ok:
        return False

    try:
        form = PrefilledForm.model_validate(result.data)
    except ValidationError:
        return False

    if form.service_id != service_id:
        return False

    form = form.model_copy(
        update={
            "form_id": f"voter-{notification_id}",
            "user_id": profile.user_id,
            "state": profile.current_state,
        }
    )
    store.save_form(form)
    _save_notice(
        Notification(
            notification_id=notification_id,
            user_id=profile.user_id,
            title="Voter-shift form is ready to review",
            body="Open the draft to review and complete your form.",
            type="form_ready",
            open_target="form",
            context_id=form.form_id,
            created_at=datetime.now(timezone.utc),
        )
    )
    return True


async def handle_message(msg: IncomingMessage, *, hub: McpHub) -> None:
    # Drop obvious OTP messages before sending any text to a tool.
    if OTP_PATTERN.search(msg.text):
        return

    async with MESSAGE_LOCK:
        if store.get_extracted(msg.message_id):
            return

        profile = store.get_profile(msg.user_id)
        if profile is None:
            return

        result = await hub.call(
            "inbox", "extract_from_message", {"message": msg.model_dump(mode="json")}
        )
        if not result.ok:
            return

        try:
            info = ExtractedInfo.model_validate(result.data)
        except ValidationError:
            return

        if not info.is_government or info.category == "otp":
            return

        # StubHub replays one example. Only accept its extraction for
        # the matching demo message shape, and take the date from the fixture.
        if result.simulated and not (
            msg.user_id == "demo_ravi"
            and msg.channel == "sms"
            and re.search(r"\bdriving licen[cs]e\b", msg.text, re.IGNORECASE)
            and re.search(r"\b(?:expir\w*|renew\w*)\b", msg.text, re.IGNORECASE)
            and re.search(r"\b0?5\s+Jan(?:uary)?\s+2027\b", msg.text, re.IGNORECASE)
        ):
            return

        doc_id = info.doc_id if info.doc_id in DOC_IDS else None
        service_id = info.service_id if info.service_id in SERVICE_IDS else None
        subject = (doc_id or service_id or "government message").replace("_", " ")
        category = info.category.replace("_", " ")

        # Persist structured fields and a generated summary. Tool-supplied
        # free text and reference numbers can contain sensitive values.
        info = info.model_copy(
            update={
                "message_id": msg.message_id,
                "doc_id": doc_id,
                "service_id": service_id,
                "summary": f"{subject.capitalize()} — {category}",
                "application_ref": None,
                "amount": None,
            }
        )

        if info.category in {"deadline", "payment_due"}:
            if not await _create_reminder(hub, profile, info):
                return

        if service_id and service_id in FORM_TEMPLATES:
            if not await _prepare_form(hub, profile, service_id):
                return

        store.save_extracted(info)