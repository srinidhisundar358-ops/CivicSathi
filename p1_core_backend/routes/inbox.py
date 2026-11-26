from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field

from p1_core_backend.db import store
from p1_core_backend.watcher.watcher_agent import handle_message
from shared.schemas import IncomingMessage


router = APIRouter()


class SmsRequest(BaseModel):
    user_id: str
    sender: str
    text: str
    channel: Literal["sms"] = "sms"
    message_id: str | None = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@router.post("/inbox/sms", status_code=202)
async def receive_sms(
    body: SmsRequest, request: Request, background_tasks: BackgroundTasks
) -> dict[str, str]:
    profile = store.get_profile(body.user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not profile.consents.sms:
        raise HTTPException(status_code=403, detail="SMS consent is required")

    message = IncomingMessage.model_validate(
        body.model_dump() | {"message_id": body.message_id or uuid4().hex}
    )
    background_tasks.add_task(
        handle_message, message, hub=request.app.state.mcp_hub
    )
    return {"status": "accepted", "message_id": message.message_id}