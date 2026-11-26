import json
import re
from datetime import datetime
from pathlib import Path

from shared.schemas import IncomingMessage, ExtractedInfo
from shared.ids import DOC_IDS, SERVICE_IDS
from shared.llm import complete_json, LlmUnavailable, is_mock

from .sender_filter import is_government


DATA_FILE = Path(__file__).resolve().parent / "data" / "patterns.json"

with DATA_FILE.open("r", encoding="utf-8") as file:
    PATTERNS = json.load(file)


CATEGORIES = [
    "deadline",
    "payment_due",
    "status_update",
    "otp",
    "info",
    "other"
]


KEYWORDS = [
    (
        r"life certificate|jeevan pramaan|pension",
        "pension_ppo",
        "pension_life_certificate"
    ),
    (
        r"driving licen[cs]e|\bDL\b",
        "driving_licence",
        "dl_renewal"
    ),
    (
        r"aadhaar|aadhar",
        "aadhaar",
        "aadhaar_address_update"
    ),
    (
        r"voter|EPIC|form 8",
        "voter_id",
        "voter_shift"
    ),
    (
        r"passport",
        "passport",
        "passport_reissue"
    ),
    (
        r"vehicle|re-registration|\bRC\b",
        "vehicle_rc",
        "vehicle_reregistration"
    ),
    (
        r"ration card|ONORC",
        "ration_card",
        "ration_card_transfer"
    ),
    (
        r"bank|KYC",
        "bank_account",
        "bank_kyc_update"
    )
]


def find_match(key, text):
    for pattern in PATTERNS.get(key, []):
        match = re.search(pattern, text)

        if match:
            return match

    return None


def parse_date(value, received_at):
    if not value:
        return None

    value = value.strip().replace(",", "")

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d %Y",
        "%B %d %Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    for fmt in formats[2:]:
        try:
            candidate = datetime.strptime(
                f"{value} {received_at.year}", fmt
            ).date()

            if candidate < received_at.date():
                candidate = candidate.replace(
                    year=candidate.year + 1
                )

            return candidate

        except ValueError:
            continue

    return None


def extract(msg: IncomingMessage) -> ExtractedInfo:
    text = msg.text
    government = is_government(msg.sender, msg.channel)

    # OTP protection: never return the code.
    if find_match("otp", text):
        return ExtractedInfo(
            message_id=msg.message_id,
            is_government=government,
            category="otp",
            summary="OTP message dropped",
            confidence=1.0
        )

    # Ignore non-government messages.
    if not government:
        return ExtractedInfo(
            message_id=msg.message_id,
            is_government=False,
            category="other",
            summary="Non-government message ignored.",
            confidence=1.0
        )

    date_match = find_match("dates", text)
    amount_match = find_match("amounts", text)
    ref_match = find_match("references", text)

    due_date = parse_date(
        date_match.group(0) if date_match else None,
        msg.received_at
    )

    amount = (
        amount_match.group(1).replace(",", "")
        if amount_match else None
    )

    application_ref = (
        ref_match.group(1) if ref_match else None
    )

    doc_id = None
    service_id = None

    for pattern, document, service in KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            doc_id = document
            service_id = service
            break

    if doc_id == "driving_licence":
        if re.search(
            r"address change|change of address",
            text,
            re.IGNORECASE
        ):
            service_id = "dl_address_change"

    if re.search(
        r"challan|payment|property tax|\bpay\b",
        text,
        re.IGNORECASE
    ):
        category = "payment_due"
        confidence = 0.95

    elif re.search(
        r"approved|received|completed|dispatched|rejected|updated",
        text,
        re.IGNORECASE
    ):
        category = "status_update"
        confidence = 0.95

    elif due_date or re.search(
        r"expires?|expiry|deadline|due by|renew|submit by",
        text,
        re.IGNORECASE
    ):
        category = "deadline"
        confidence = 0.95 if due_date else 0.75

    elif doc_id:
        category = "info"
        confidence = 0.65

    else:
        category = "other"
        confidence = 0.4

    result = ExtractedInfo(
        message_id=msg.message_id,
        is_government=True,
        category=category,
        doc_id=doc_id,
        service_id=service_id,
        due_date=due_date,
        amount=amount,
        application_ref=application_ref,
        summary="Government message identified.",
        confidence=confidence
    )

    # Optional AI classification.
    # Only structured information is sent, not raw messages.
    if not is_mock():
        prompt = (
            "Classify this government message using only "
            "the supplied extracted information. "
            "Do not invent missing facts. "
            f"Allowed document IDs: {list(DOC_IDS)}. "
            f"Allowed service IDs: {list(SERVICE_IDS)}. "
            f"Allowed categories: {CATEGORIES}. "
            f"Extracted information: "
            f"{result.model_dump_json(exclude={'application_ref'})}"
        )

        try:
            ai_result = complete_json(prompt, ExtractedInfo)

            if ai_result.category != "otp":
                result.category = ai_result.category
                result.doc_id = ai_result.doc_id
                result.service_id = ai_result.service_id
                result.confidence = ai_result.confidence

        except LlmUnavailable:
            pass

    # Validate against shared team IDs.
    if result.doc_id not in DOC_IDS:
        result.doc_id = None

    if result.service_id not in SERVICE_IDS:
        result.service_id = None

    result.confidence = max(
        0.0, min(1.0, result.confidence)
    )

    if result.confidence < 0.5:
        result.category = "other"

    # Generate a safe summary without copying raw text.
    subject = (
        result.doc_id.replace("_", " ").capitalize()
        if result.doc_id else "Government message"
    )

    if result.category == "deadline":
        result.summary = f"{subject}: action required"

        if result.due_date:
            result.summary += f" by {result.due_date}"

    elif result.category == "payment_due":
        result.summary = "Government payment due"

        if result.amount:
            result.summary += f": INR {result.amount}"

    elif result.category == "status_update":
        result.summary = f"{subject}: application status updated"

    elif result.category == "info":
        result.summary = f"{subject}: information received"

    else:
        result.summary = "Message could not be classified confidently."

    return result
