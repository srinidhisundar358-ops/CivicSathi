from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from datetime import date, timedelta
from urllib.parse import urlencode
from uuid import uuid4

from fastapi.responses import HTMLResponse

from shared.schemas import HeldDocument, Notification, PersonalDetails, Reminder
from datetime import datetime, timezone

from p1_core_backend.db import store


router = APIRouter()


class ConnectRequest(BaseModel):
    user_id: str


@router.post("/connect/digilocker/start")
async def start_digilocker(body: ConnectRequest, request: Request) -> dict:
    if store.get_profile(body.user_id) is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = await request.app.state.mcp_hub.call(
        "digilocker", "start_consent", {"user_id": body.user_id}
    )
    data = result.data if isinstance(result.data, dict) else {}
    url = data.get("url")
    if not result.ok or not isinstance(url, str) or not url:
        raise HTTPException(status_code=502, detail="Could not start DigiLocker consent")

    return {"url": url, "simulated": result.simulated}
def _demo_profile(user_id: str, request_id: str):
    # The current stub consent URL contains these fixed demo values.
    if (user_id, request_id) != ("demo_ravi", "demo_request"):
        raise HTTPException(status_code=404, detail="Demo consent request not found")
    profile = store.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.get("/connect/digilocker/mock-consent", response_class=HTMLResponse)
def mock_consent(user_id: str, request_id: str) -> str:
    _demo_profile(user_id, request_id)
    return f"""
    <h1>DigiLocker (simulated)</h1>
    <p>Allow CivicSaathi to read your demo documents?</p>
    <form action="/connect/digilocker/callback" method="get">
        <input type="hidden" name="user_id" value="{user_id}">
        <input type="hidden" name="request_id" value="{request_id}">
        <button type="submit">Allow</button>
    </form>
    """


@router.get("/connect/digilocker/callback", response_class=HTMLResponse)
async def digilocker_callback(user_id: str, request_id: str, request: Request) -> str:
    profile = _demo_profile(user_id, request_id)
    hub = request.app.state.mcp_hub
    user_args = {"user_id": user_id}

    consent = await hub.call(
        "digilocker", "complete_consent", {**user_args, "request_id": request_id}
    )
    if not (consent.ok and consent.data == {"approved": True}):
        raise HTTPException(status_code=502, detail="Demo consent could not be completed")

    documents = await hub.call("digilocker", "list_documents", user_args)
    identity = await hub.call("digilocker", "get_identity_details", user_args)
    if not (documents.ok and isinstance(documents.data, list) and identity.ok):
        raise HTTPException(status_code=502, detail="Could not load demo documents")

    personal = PersonalDetails.model_validate(identity.data)
    imported = [HeldDocument.model_validate(item) for item in documents.data]
    merged = {doc.doc_id: doc for doc in profile.documents}
    for doc in imported:
        merged[doc.doc_id] = doc.model_copy(update={"origin": "digilocker"})

    for doc in imported:
        if doc.expiry_date is None:
            continue

        rule = await hub.call("deadlines", "get_renewal_rule", {"doc_id": doc.doc_id})
        data = rule.data if rule.ok and isinstance(rule.data, dict) else {}
        days = data.get("renew_before_days")
        if type(days) is not int or not 0 <= days <= 365:
            days = 30

        reminder = Reminder(
            reminder_id=uuid4().hex,
            user_id=user_id,
            doc_id=doc.doc_id,
            title=f"Review {doc.doc_id.replace('_', ' ')} renewal",
            due_date=max(date.today(), doc.expiry_date - timedelta(days=days)),
        )
        saved = await hub.call(
            "deadlines", "add_reminder", {"reminder": reminder.model_dump(mode="json")}
        )
        if not saved.ok:
            raise HTTPException(status_code=502, detail="Could not save renewal reminder")

    was_connected = profile.consents.digilocker
    profile.personal = personal
    profile.documents = list(merged.values())
    profile.consents.digilocker = True
    store.save_profile(profile)

    if not was_connected:
        store.save_notification(
            Notification(
                notification_id=uuid4().hex,
                user_id=user_id,
                title="DigiLocker connected",
                body="Your simulated documents are ready to review.",
                type="connected",
                open_target="home",
                created_at=datetime.now(timezone.utc),
            )
        )

    target = "civicsaathi://connected?" + urlencode({"source": "digilocker"})
    return f"""
    <meta http-equiv="refresh" content="0;url={target}">
    <h1>DigiLocker connected (simulated)</h1>
    <a href="{target}">Return to app</a>
    """
@router.post("/connect/gmail/start")
def start_gmail(body: ConnectRequest) -> dict[str, bool]:
    profile = store.get_profile(body.user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile.consents.gmail = True
    store.save_profile(profile)
    return {"simulated": True}
@router.get("/connect/digilocker/start")
async def get_digilocker_start(user_id: str, request: Request) -> dict:
    return await start_digilocker(ConnectRequest(user_id=user_id), request)


@router.get("/connect/gmail/start")
def get_gmail_start(user_id: str) -> dict[str, bool]:
    return start_gmail(ConnectRequest(user_id=user_id))


@router.get("/connect/gmail/callback", response_class=HTMLResponse)
def gmail_callback(user_id: str) -> str:
    profile = store.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not profile.consents.gmail:
        raise HTTPException(status_code=409, detail="Start Gmail consent first")

    target = "civicsaathi://connected?source=gmail"
    return f"""
    <meta http-equiv="refresh" content="0;url={target}">
    <h1>Gmail connected (simulated)</h1>
    <a href="{target}">Return to app</a>
    """


@router.post("/connect/{source}/revoke")
async def revoke_connection(
    source: str, body: ConnectRequest, request: Request
) -> dict[str, bool]:
    if source not in {"digilocker", "gmail"}:
        raise HTTPException(status_code=404, detail="Unknown connection source")

    profile = store.get_profile(body.user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    if source == "digilocker" and profile.consents.digilocker:
        result = await request.app.state.mcp_hub.call(
            "digilocker", "revoke", {"user_id": body.user_id}
        )
        if not result.ok:
            raise HTTPException(status_code=502, detail="Could not revoke DigiLocker")

    if source == "digilocker":
        profile.consents.digilocker = False
    else:
        profile.consents.gmail = False

    store.save_profile(profile)
    return {"revoked": True}