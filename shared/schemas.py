from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel



class Source(BaseModel):
    title: str
    url: str
    last_verified: date


class ToolResult(BaseModel):          # EVERY MCP tool returns this envelope
    ok: bool
    data: Any = None
    error: str | None = None
    simulated: bool = False
    sources: list[Source] = []


class Address(BaseModel):
    line1: str
    city: str
    district: str | None = None
    state: str
    pincode: str


class PersonalDetails(BaseModel):     # NEVER store Aadhaar / EPIC / PAN / bank numbers
    full_name: str
    dob: date | None = None
    relative_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: Address | None = None


class HeldDocument(BaseModel):
    doc_id: str
    issued_state: str | None = None
    address_state: str | None = None
    expiry_date: date | None = None
    origin: Literal["user", "digilocker"] = "user"


class Consents(BaseModel):
    sms: bool = False
    gmail: bool = False
    digilocker: bool = False


class UserProfile(BaseModel):
    user_id: str
    language: Literal["en", "hi", "kn", "mr"] = "en"
    age: int | None = None
    birth_state: str | None = None
    current_state: str
    personal: PersonalDetails | None = None
    documents: list[HeldDocument] = []
    consents: Consents = Consents()


class LifeEvent(BaseModel):
    event_type: str
    from_state: str | None = None
    to_state: str | None = None
    event_date: date | None = None


class ChecklistItem(BaseModel):
    doc_id: str
    service_id: str
    action: str
    priority: Literal["mandatory", "recommended", "depends"]
    reason: str
    steps: list[str]
    required_docs: list[str]
    fee: str | None = None
    official_link: str | None = None
    deadline: date | None = None
    sources: list[Source] = []        # empty list = show as "unverified"


class ActionPlan(BaseModel):
    summary: str
    items: list[ChecklistItem]
    reminders_created: list[str] = []


class Reminder(BaseModel):
    reminder_id: str
    user_id: str
    doc_id: str | None = None
    title: str
    due_date: date
    channel: Literal["app", "voice_call"] = "app"
    source_message_id: str | None = None


class IncomingMessage(BaseModel):
    message_id: str
    user_id: str
    channel: Literal["sms", "email"]
    sender: str
    text: str
    received_at: datetime


class ExtractedInfo(BaseModel):
    message_id: str
    is_government: bool
    category: Literal["deadline", "payment_due", "status_update", "otp", "info", "other"]
    doc_id: str | None = None
    service_id: str | None = None
    due_date: date | None = None
    amount: str | None = None
    application_ref: str | None = None
    summary: str
    confidence: float


class Notification(BaseModel):
    notification_id: str
    user_id: str
    title: str
    body: str
    type: Literal["reminder", "alert", "form_ready", "connected"]
    open_target: Literal["chat", "form", "home"]
    context_id: str | None = None
    created_at: datetime
    read: bool = False


class FormField(BaseModel):
    field_id: str
    label: str
    value: str | None = None
    source: Literal["profile", "digilocker", "user"]
    required: bool = True
    needs_user_input: bool = False


class PrefilledForm(BaseModel):
    form_id: str
    user_id: str
    service_id: str
    state: str
    fields: list[FormField]
    missing: list[str] = []
    official_link: str
    status: Literal["draft", "reviewed"] = "draft"
