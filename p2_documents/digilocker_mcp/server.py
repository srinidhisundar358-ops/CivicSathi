from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from shared.ports import DIGILOCKER
from shared.schemas import ToolResult


mcp = FastMCP(
    "digilocker",
    host="0.0.0.0",
    port=DIGILOCKER,
)


# This is an in-memory demo consent store.
# It is not real DigiLocker authentication or OAuth.
CONSENT_REQUESTS = {}
APPROVED_USERS = set()


DEMO_DOCUMENTS = [
    {
        "doc_id": "driving_licence",
        "issued_state": "karnataka",
        "expiry_date": "2027-01-05",
        "origin": "digilocker",
    }
]


DEMO_IDENTITY = {
    "full_name": "Ravi Kumar",
    "address": {
        "line1": "10 Demo Lane",
        "city": "Bengaluru",
        "state": "karnataka",
        "pincode": "560001",
    },
}


def response(data, simulated=True):
    return ToolResult(
        ok=True,
        data=data,
        simulated=simulated,
    ).model_dump(mode="json")


def error_response(message, simulated=True):
    return ToolResult(
        ok=False,
        error=str(message),
        simulated=simulated,
    ).model_dump(mode="json")


@mcp.tool()
def ping() -> dict:
    """Check DigiLocker MCP health."""
    return response("pong")


@mcp.tool()
def start_consent(user_id: str) -> dict:
    """
    Start a simulated DigiLocker consent request.

    The returned URL is a local mock-consent page.
    It does not connect to a real DigiLocker account.
    """

    if not user_id or not user_id.strip():
        return error_response("user_id is required.")

    user_id = user_id.strip()
    request_id = "demo_request"

    CONSENT_REQUESTS[user_id] = request_id
    APPROVED_USERS.discard(user_id)

    consent_url = (
        "http://localhost:8000/connect/digilocker/mock-consent"
        f"?user_id={quote(user_id)}"
        f"&request_id={quote(request_id)}"
    )

    return response({
        "id": request_id,
        "url": consent_url,
    })


@mcp.tool()
def complete_consent(
    user_id: str,
    request_id: str,
) -> dict:
    """
    Complete the simulated consent flow.

    Consent is granted only when the user and request ID match
    a previously started demo request.
    """

    expected_request = CONSENT_REQUESTS.get(user_id)

    if expected_request is None:
        return error_response(
            "No active consent request exists for this user."
        )

    if request_id != expected_request:
        return error_response(
            "The consent request ID does not match."
        )

    APPROVED_USERS.add(user_id)

    return response({
        "approved": True,
    })


@mcp.tool()
def list_documents(user_id: str) -> dict:
    """List demo DigiLocker documents after consent."""

    if user_id not in APPROVED_USERS:
        return error_response(
            "User consent is required before listing documents."
        )

    # Return copies so callers cannot mutate the demo fixtures.
    documents = [
        dict(document)
        for document in DEMO_DOCUMENTS
    ]

    return response(documents)


@mcp.tool()
def get_identity_details(user_id: str) -> dict:
    """Return demo identity details after consent."""

    if user_id not in APPROVED_USERS:
        return error_response(
            "User consent is required before accessing identity details."
        )

    identity = {
        "full_name": DEMO_IDENTITY["full_name"],
        "address": dict(DEMO_IDENTITY["address"]),
    }

    return response(identity)


@mcp.tool()
def revoke(user_id: str) -> dict:
    """
    Revoke the user's simulated consent.

    Future document and identity requests will be rejected.
    """

    APPROVED_USERS.discard(user_id)
    CONSENT_REQUESTS.pop(user_id, None)

    return response({
        "revoked": True,
    })


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
