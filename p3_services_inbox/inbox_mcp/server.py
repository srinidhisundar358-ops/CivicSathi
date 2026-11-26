
import re
from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("CivicSaathi Inbox")


def extract_message(message: str):
    text = message.lower()

    # Ignore verification messages without retaining their contents
    verification_terms = [
        "otp",
        "one time password",
        "verification code",
        "verify your login",
    ]

    if any(term in text for term in verification_terms):
        return {"category": "ignored"}

    category = "unknown"
    service_id = None

    # Identify the government service
    if "driving licence" in text or "driving license" in text:
        category = "driving_licence"
        service_id = "dl_renewal"

    elif "voter" in text or "epic" in text:
        category = "voter"
        service_id = "voter_shift"

    elif "pension" in text or "life certificate" in text:
        category = "pension"
        service_id = "pension_life_certificate"

    elif "aadhaar" in text:
        category = "aadhaar"
        service_id = "aadhaar_address_update"

    elif "passport" in text:
        category = "passport"
        service_id = "passport_reissue"

    elif "ration card" in text:
        category = "ration_card"
        service_id = "ration_card_transfer"

    action = None

    # Identify a broad action
    if any(word in text for word in ["submit", "upload"]):
        action = "submit_document"

    elif "visit" in text:
        action = "visit_office"

    elif "update" in text:
        action = "update_information"

    # Recognise common numeric date formats
    date_patterns = [
        r"\b\d{2}-\d{2}-\d{4}\b",
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    ]

    due_date = None

    for pattern in date_patterns:
        match = re.search(pattern, message)
        if match:
            due_date = match.group(0)
            break

    return {
        "category": category,
        "service_id": service_id,
        "action": action,
        "due_date": due_date,
    }


@mcp.tool()
def extract_from_message(message: str):
    """Extract basic structured information from a supplied message."""
    return extract_message(message)


@mcp.tool()
def is_government_sender(sender: str, channel: str = "email"):
    """Demo-only sender check. A match does not prove authenticity."""

    if channel != "email":
        return False

    sender = sender.strip().lower()

    if "@" not in sender:
        return False

    domain = sender.rsplit("@", 1)[-1]

    # Temporary demo allowlist only.
    # This will be moved into gov_senders.json.
    demo_domains = {
        "demo.gov.in",
        "example.gov.in",
    }

    return domain in demo_domains


if __name__ == "__main__":
    mcp.run()

