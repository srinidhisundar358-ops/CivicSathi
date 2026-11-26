import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from p1_core_backend.deadlines_mcp import store
from shared.ports import DEADLINES
from shared.schemas import Reminder, ToolResult


mcp = FastMCP("deadlines", host="0.0.0.0", port=DEADLINES)
RULES_PATH = Path(__file__).with_name("data") / "renewal_rules.json"


@mcp.tool()
def ping() -> dict:
    return ToolResult(ok=True, data="pong").model_dump(mode="json")


@mcp.tool()
def add_reminder(reminder: Reminder) -> dict:
    saved = store.add(reminder)
    return ToolResult(ok=True, data=saved).model_dump(mode="json")


@mcp.tool()
def list_upcoming(user_id: str, days: int = 7) -> dict:
    if not 0 <= days <= 365:
        return ToolResult(
            ok=False, error="days must be between 0 and 365"
        ).model_dump(mode="json")

    return ToolResult(
        ok=True, data=store.upcoming(user_id, days)
    ).model_dump(mode="json")


@mcp.tool()
def check_overdue(user_id: str) -> dict:
    return ToolResult(
        ok=True, data=store.overdue(user_id)
    ).model_dump(mode="json")


@mcp.tool()
def get_renewal_rule(doc_id: str) -> dict:
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    rule = rules.get(doc_id)
    if rule is None:
        return ToolResult(
            ok=False, error="No renewal rule for this document"
        ).model_dump(mode="json")

    return ToolResult(ok=True, data={"doc_id": doc_id, **rule}).model_dump(
        mode="json"
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")