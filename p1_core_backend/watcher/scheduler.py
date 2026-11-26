from datetime import date, datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError

from p1_core_backend.db import store
from p1_core_backend.mcp_client.hub import McpHub
from p1_core_backend.watcher.watcher_agent import handle_message
from p4_voice_notify.push.fcm import send_push
from shared.ids import DOC_IDS
from shared.schemas import IncomingMessage, Notification, Reminder


async def run_once(*, hub: McpHub) -> dict[str, int]:
    today = date.today()
    cutoff = today + timedelta(days=7)
    counts = {"notifications_created": 0, "emails_checked": 0}

    for profile in store.list_profiles():
        for tool, extra_args in (
            ("list_upcoming", {"days": 7}),
            ("check_overdue", {}),
        ):
            result = await hub.call(
                "deadlines", tool, {"user_id": profile.user_id, **extra_args}
            )
            if not result.ok or not isinstance(result.data, list):
                continue

            for payload in result.data:
                try:
                    reminder = Reminder.model_validate(payload)
                except ValidationError:
                    continue

                if reminder.user_id != profile.user_id or reminder.due_date > cutoff:
                    continue
                if tool == "check_overdue" and reminder.due_date >= today:
                    continue
                if tool == "list_upcoming" and reminder.due_date < today:
                    continue

                overdue = reminder.due_date < today
                notification_id = uuid5(
                    NAMESPACE_URL,
                    f"civicsaathi:scheduler:{profile.user_id}:"
                    f"{reminder.reminder_id}:{today.isoformat()}",
                ).hex
                if store.get_notification(notification_id):
                    continue

                subject = (
                    reminder.doc_id.replace("_", " ").capitalize()
                    if reminder.doc_id in DOC_IDS
                    else "Document"
                )
                notice = Notification(
                    notification_id=notification_id,
                    user_id=profile.user_id,
                    title=f"{subject} {'overdue' if overdue else 'reminder'}",
                    body=f"Due date: {reminder.due_date.isoformat()}",
                    type="alert" if overdue else "reminder",
                    open_target="chat" if reminder.source_message_id else "home",
                    context_id=reminder.source_message_id,
                    created_at=datetime.now(timezone.utc),
                )
                store.save_notification(notice)
                send_push(notice.model_dump(mode="json"))
                counts["notifications_created"] += 1

        if not profile.consents.gmail:
            continue

        result = await hub.call(
            "inbox",
            "fetch_recent_emails",
            {"user_id": profile.user_id, "since_hours": 24},
        )
        if not result.ok or not isinstance(result.data, list):
            continue

        for payload in result.data:
            try:
                message = IncomingMessage.model_validate(payload)
            except ValidationError:
                continue

            if message.user_id == profile.user_id and message.channel == "email":
                await handle_message(message, hub=hub)
                counts["emails_checked"] += 1

    return counts