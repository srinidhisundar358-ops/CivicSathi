from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from p1_core_backend.db import store
from p1_core_backend.deadlines_mcp import store as deadlines_store
from p1_core_backend.main import app
from p1_core_backend.mcp_client import hub
from p1_core_backend.mcp_client.stubs import StubHub
from shared.schemas import Reminder, ToolResult


@pytest.fixture
def client(tmp_path, monkeypatch):
    settings = replace(hub.settings, db_path=tmp_path / "test.db", use_stubs=True)
    monkeypatch.setattr(hub, "settings", settings)
    monkeypatch.setattr(store, "settings", settings)
    monkeypatch.setenv("LLM_MODE", "mock")

    # Use the real SQLite reminder store without starting another server.
    stub_call = StubHub.call

    def call_with_reminder_storage(self, server, tool, args):
        if (server, tool) == ("deadlines", "add_reminder"):
            reminder = Reminder.model_validate(args["reminder"])
            saved = deadlines_store.add(reminder)
            return ToolResult(ok=True, data=saved.model_dump(mode="json"))
        return stub_call(self, server, tool, args)

    monkeypatch.setattr(StubHub, "call", call_with_reminder_storage)
    with TestClient(app) as test_client:
        yield test_client


def test_relocation_starts_with_aadhaar(client):
    response = client.post(
        "/chat",
        json={
            "user_id": "demo_ravi",
            "message": "I was born in Bengaluru. My family is shifting to Pune.",
        },
    )
    assert response.status_code == 200
    items = response.json()["plan"]["items"]
    assert len(items) >= 3
    assert items[0]["doc_id"] == "aadhaar"


def test_licence_sms_creates_reminder_and_otp_is_ignored(client):
    sms = {"user_id": "demo_ravi", "sender": "DEMO-DL"}
    response = client.post(
        "/inbox/sms",
        json={
            **sms,
            "message_id": "licence-test",
            "text": "Demo: your driving licence expires 05 Jan 2027.",
        },
    )
    assert response.status_code == 202
    notices = client.get("/notifications/demo_ravi").json()
    assert len(notices) == 1
    assert notices[0]["type"] == "reminder"
    assert notices[0]["context_id"] == "licence-test"

    response = client.post(
        "/inbox/sms",
        json={**sms, "message_id": "otp-test", "text": "Your OTP is 123456"},
    )
    assert response.status_code == 202
    assert client.get("/notifications/demo_ravi").json() == notices
    assert store.get_extracted("otp-test") is None


def test_digilocker_imports_licence_and_saves_reminder(client):
    start = client.post("/connect/digilocker/start", json={"user_id": "demo_ravi"})
    assert start.status_code == 200
    assert start.json()["simulated"] is True

    callback = client.get(
        "/connect/digilocker/callback",
        params={"user_id": "demo_ravi", "request_id": "demo_request"},
    )
    assert callback.status_code == 200
    profile = client.get("/profile/demo_ravi").json()
    assert profile["consents"]["digilocker"] is True
    assert any(
        doc["doc_id"] == "driving_licence" and doc["origin"] == "digilocker"
        for doc in profile["documents"]
    )
    assert any(
        reminder.doc_id == "driving_licence"
        for reminder in deadlines_store.upcoming("demo_ravi", 365)
    )


def test_voice_stream_ends_with_done(client):
    response = client.post(
        "/v1/chat/completions",
        json={
            "user": "demo_ravi",
            "stream": True,
            "messages": [{"role": "user", "content": "I am moving to Pune."}],
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"role": "assistant"' in response.text
    assert '"content":' in response.text
    assert '"finish_reason": "stop"' in response.text
    assert response.text.endswith("data: [DONE]\n\n")