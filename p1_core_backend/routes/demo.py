import json

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from p1_core_backend.config import REPO_ROOT
from p1_core_backend.routes.inbox import SmsRequest, receive_sms
from p1_core_backend.db import store
from p1_core_backend.watcher.scheduler import run_once


router = APIRouter()


@router.post("/demo/run-scheduler")
async def run_scheduler(request: Request) -> dict[str, int]:
    return await run_once(hub=request.app.state.mcp_hub)
@router.post("/demo/reset")
def reset_demo() -> dict[str, str]:
    store.reset_demo()
    return {"status": "reset"}
SAMPLE_MESSAGES = (
    REPO_ROOT / "p3_services_inbox" / "tests" / "sample_messages.json"
)


class SimulateSmsRequest(BaseModel):
    user_id: str
    sample_index: int = Field(ge=0)


@router.post("/demo/simulate-sms", status_code=202)
async def simulate_sms(
    body: SimulateSmsRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    try:
        if SAMPLE_MESSAGES.is_file():
            samples = json.loads(SAMPLE_MESSAGES.read_text(encoding="utf-8"))
        else:
            shared_path = REPO_ROOT / "shared" / "samples.json"
            shared = json.loads(shared_path.read_text(encoding="utf-8"))
            samples = [{"message": message} for message in shared["messages"]]
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="SMS samples are unavailable") from exc

    if not isinstance(samples, list):
        raise HTTPException(status_code=503, detail="Invalid SMS sample file")
    if body.sample_index >= len(samples):
        raise HTTPException(status_code=404, detail="SMS sample index not found")

    entry = samples[body.sample_index]
    message = entry.get("message") if isinstance(entry, dict) else None
    if not isinstance(message, dict) or message.get("channel") != "sms":
        raise HTTPException(status_code=422, detail="Selected sample is not an SMS")

    try:
        sms = SmsRequest.model_validate(
            message | {"user_id": body.user_id, "message_id": None}
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid SMS sample") from exc

    return await receive_sms(sms, request, background_tasks)
