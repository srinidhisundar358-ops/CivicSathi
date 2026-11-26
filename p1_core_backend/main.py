from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from p1_core_backend.db import store
from p1_core_backend.mcp_client.hub import McpHub
from p1_core_backend.routes import chat, demo, forms, inbox, notifications, trace, connect, profile, llm_compat, devices
@asynccontextmanager
async def lifespan(app: FastAPI):
    store.seed_demo()
    hub = McpHub()
    await hub.startup()
    app.state.mcp_hub = hub
    yield


app = FastAPI(title="CivicSaathi", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat.router)
app.include_router(inbox.router)
app.include_router(notifications.router)
app.include_router(demo.router)
app.include_router(trace.router)
app.include_router(forms.router)
app.include_router(connect.router)
app.include_router(profile.router)
app.include_router(llm_compat.router)
app.include_router(devices.router)
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}