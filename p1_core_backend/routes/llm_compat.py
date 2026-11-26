import json
import re
from time import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from p1_core_backend.agent.orchestrator import run_chat


router = APIRouter()


class VoiceMessage(BaseModel):
    role: str
    content: str


class VoiceRequest(BaseModel):
    messages: list[VoiceMessage]
    model: str = "civicsaathi"
    stream: bool = False
    user: str | None = None
    elevenlabs_extra_body: dict = Field(default_factory=dict)


@router.post("/v1/chat/completions")
async def voice_chat(body: VoiceRequest, request: Request):
    question = next(
        (message.content for message in reversed(body.messages)
         if message.role == "user"),
        "",
    )
    if not question.strip():
        raise HTTPException(status_code=422, detail="A user message is required")

    extra_user = body.elevenlabs_extra_body.get("user_id")
    user_id = (
        body.user
        or (extra_user if isinstance(extra_user, str) else None)
        or request.headers.get("X-User-Id")
        or "demo_ajji"
    )
    reply, _, conversation_id = await run_chat(
        user_id,
        question,
        hub=request.app.state.mcp_hub,
    )
    reply = re.sub(r"https?://\S+", "", reply)
    reply = " ".join(reply.replace("**", "").replace("`", "").split())

    metadata = {
        "id": f"chatcmpl-{conversation_id}",
        "created": int(time()),
        "model": body.model,
    }

    if not body.stream:
        return {
            **metadata,
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }],
        }

    def chunk(delta: dict, finish_reason: str | None = None) -> str:
        payload = {
            **metadata,
            "object": "chat.completion.chunk",
            "choices": [{
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }],
        }
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def events():
        yield chunk({"role": "assistant"})
        for text in re.split(r"(?<=[.!?])(?=\s)", reply):
            if text:
                yield chunk({"content": text})
        yield chunk({}, "stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")