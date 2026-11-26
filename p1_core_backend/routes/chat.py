from fastapi import APIRouter, Request
from pydantic import BaseModel

from p1_core_backend.agent.orchestrator import run_chat
from shared.schemas import ActionPlan


router = APIRouter()


class ChatRequest(BaseModel):
    user_id: str
    message: str
    context_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    plan: ActionPlan | None = None
    conversation_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    reply, plan, conversation_id = await run_chat(
        body.user_id,
        body.message,
        body.context_id,
        hub=request.app.state.mcp_hub,
    )
    return ChatResponse(
        reply=reply,
        plan=plan,
        conversation_id=conversation_id,
    )