from mcp.server.fastmcp import FastMCP

from shared.schemas import IncomingMessage, ToolResult
from shared.ports import INBOX

from .extractor import extract
from .sender_filter import is_government
from .gmail_client import consent_url, exchange_code, fetch


mcp = FastMCP(
    "inbox",
    host="0.0.0.0",
    port=INBOX
)


@mcp.tool()
def extract_from_message(message: IncomingMessage) -> dict:
    result = extract(message)

    return ToolResult(
        ok=True,
        data=result.model_dump(mode="json")
    ).model_dump(mode="json")


@mcp.tool()
def is_government_sender(sender: str, channel: str) -> dict:
    return ToolResult(
        ok=True,
        data=is_government(sender, channel)
    ).model_dump(mode="json")


@mcp.tool()
def start_gmail_consent(user_id: str) -> dict:
    return ToolResult(
        ok=True,
        data=consent_url(user_id),
        simulated=True
    ).model_dump(mode="json")


@mcp.tool()
def complete_gmail_consent(user_id: str, code: str) -> dict:
    return ToolResult(
        ok=True,
        data=exchange_code(user_id, code),
        simulated=True
    ).model_dump(mode="json")


@mcp.tool()
def fetch_recent_emails(
    user_id: str,
    since_hours: int = 24
) -> dict:

    messages = fetch(user_id, since_hours)

    return ToolResult(
        ok=True,
        data=[
            message.model_dump(mode="json")
            for message in messages
        ],
        simulated=True
    ).model_dump(mode="json")

@mcp.tool()
def ping() -> dict:
    return ToolResult(ok=True, data="pong").model_dump(mode="json")
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
