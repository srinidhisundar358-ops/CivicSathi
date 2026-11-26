import json
from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from p1_core_backend.db import store


router = APIRouter()

COLUMNS = (
    "Server", "Tool", "Arguments", "OK", "Simulated", "Source", "Duration (ms)"
)


@router.get("/trace/{conversation_id}")
def get_trace(conversation_id: str) -> list[dict]:
    return store.list_traces(conversation_id)


@router.get("/trace/{conversation_id}/view", response_class=HTMLResponse)
def view_trace(conversation_id: str) -> str:
    headings = "".join(f"<th>{escape(label)}</th>" for label in COLUMNS)
    rows = []

    for entry in store.list_traces(conversation_id):
        result = entry["result"]
        values = (
            entry["server"],
            entry["tool"],
            json.dumps(entry["args"], ensure_ascii=False),
            result["ok"],
            result["simulated"],
            entry["source"],
            f'{entry["duration_ms"]:.1f}',
        )
        cells = "".join(f"<td>{escape(str(value))}</td>" for value in values)
        rows.append(f"<tr>{cells}</tr>")

    body = "".join(rows)
    if not body:
        body = '<tr><td colspan="7">No MCP calls recorded.</td></tr>'

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>CivicSaathi MCP Trace</title>
</head>
<body>
    <h1>MCP trace</h1>
    <p>Conversation <code>{escape(conversation_id)}</code></p>
    <table>
        <thead><tr>{headings}</tr></thead>
        <tbody>{body}</tbody>
    </table>
</body>
</html>"""