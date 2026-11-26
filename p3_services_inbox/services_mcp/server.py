from mcp.server.fastmcp import FastMCP

from shared.schemas import ToolResult
from shared.ports import SERVICES
from shared.ids import SERVICE_IDS

from .rules import lookup, load_data


mcp = FastMCP(
    "services",
    host="0.0.0.0",
    port=SERVICES
)


@mcp.tool()
def get_process(service_id: str, state: str) -> dict:
    service = (
        lookup(service_id, state)
        if service_id in SERVICE_IDS
        else None
    )

    if service is None:
        return ToolResult(
            ok=True,
            data={
                "service_id": service_id,
                "state": state,
                "authority": None,
                "official_link": None,
                "steps": [],
                "fee": None,
                "required_docs": [],
                "processing_time": None,
                "verified": False
            },
            error="unverified: not in our official data"
        ).model_dump(mode="json")

    return ToolResult(
        ok=True,
        data={
            "service_id": service_id,
            "state": state,
            "authority": service.get("authority"),
            "official_link": service.get("official_link"),
            "steps": service.get("steps") or [],
            "fee": service.get("fee"),
            "required_docs": service.get("required_docs") or [],
            "processing_time": service.get("processing_time"),
            "verified": service.get("verified", False)
        },
        sources=service.get("sources") or []
    ).model_dump(mode="json")


@mcp.tool()
def get_authority(service_id: str, state: str) -> dict:
    service = (
        lookup(service_id, state)
        if service_id in SERVICE_IDS
        else None
    ) or {}

    return ToolResult(
        ok=True,
        data={
            "authority": service.get("authority"),
            "portal_name": service.get("portal_name"),
            "official_link": service.get("official_link")
        },
        sources=service.get("sources") or []
    ).model_dump(mode="json")


@mcp.tool()
def explain_term(term: str, language: str) -> dict:
    glossary = load_data("glossary.json")

    entry = next(
        (
            value
            for key, value in glossary.items()
            if key.strip().lower() == term.strip().lower()
        ),
        {}
    )

    explanation = (
        entry.get(language.lower())
        or entry.get("en")
        or "not in glossary"
    )

    return ToolResult(
        ok=True,
        data={
            "term": term,
            "language": language,
            "explanation": explanation
        }
    ).model_dump(mode="json")

@mcp.tool()
def ping() -> dict:
    return ToolResult(ok=True, data="pong").model_dump(mode="json")
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
