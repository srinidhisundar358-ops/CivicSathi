
import re
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("CivicSaathi Inbox")


def extract_message(message: str):
    text = message.lower()

    # Discard verification messages without processing further
    if any(word in text for word in [
        "otp", "one time password", "verification code"
    ]):
        return {"category": "ignored"}

    category = "unknown"
    service_id = None

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

    action = None

    if "submit" in text or "upload" in text:
        action = "submit_document"
    elif "visit" in text:
        action = "visit_office"
    elif "update" in text:
        action = "update_information"

    date_match = re.search(
        r"\b\d{2}-\d{2}-\d{4}\b", message
    )

    return {
        "category": category,
        "service_id": service_id,
        "action": action,
        "due_date": date_match.group(0) if date_match else None
    }


@mcp.tool()
def extract_from_message(message: str):
    """Extract basic information from a synthetic message."""
    return extract_message(message)


@mcp.tool()
def is_government_sender(sender: str, channel: str = "email"):
    """Demo-only check against a configured example list."""
    if channel != "email":
        return False

    sender = sender.strip().lower()

    if "@" not in sender:
        return False

    domain = sender.split("@")[-1]

    return domain in {"demo.gov.in", "example.gov.in"}


if __name__ == "__main__":
    mcp.run()

