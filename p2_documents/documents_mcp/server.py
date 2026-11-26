from mcp.server.fastmcp import FastMCP

from shared.ports import DOCUMENTS
from shared.schemas import ToolResult

from p2_documents.documents_mcp.processor import (
    process_document,
    classify_document,
)

from p2_documents.formfill_mcp.service_client import call_service_tool


mcp = FastMCP(
    "documents",
    host="0.0.0.0",
    port=DOCUMENTS,
)


def response(data, simulated=False):
    return ToolResult(
        ok=True,
        data=data,
        simulated=simulated,
    ).model_dump(mode="json")


def error_response(message):
    return ToolResult(
        ok=False,
        error=str(message),
    ).model_dump(mode="json")


@mcp.tool()
def ping() -> dict:
    """Check whether Documents MCP is running."""
    return response("pong")


@mcp.tool()
def upload_and_process_document(
    filename: str,
    content_base64: str,
) -> dict:
    """
    Extract text from an uploaded PDF or image.

    Identity-number patterns are redacted from returned text.
    The document is not permanently stored.
    """

    try:
        result = process_document(filename, content_base64)
        return response(result)

    except Exception as exc:
        return error_response(exc)


@mcp.tool()
def identify_document(text: str) -> dict:
    """
    Identify a likely document type from extracted text.

    The result is a suggestion and must be confirmed by the user.
    """

    try:
        return response(classify_document(text))
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
def get_affected_documents(
    event: dict,
    held: list[dict],
) -> dict:
    """
    Identify documents that may need attention after a life event.

    The output follows the P1 plan_builder contract:
    a list of records containing doc_id, service_id, priority,
    reason and held.

    This is a checklist suggestion, not a legal determination.
    """

    try:
        event_type = str(event.get("event_type", "")).lower()
        from_state = str(event.get("from_state") or "").lower()
        to_state = str(event.get("to_state") or "").lower()

        held_ids = {
            str(doc.get("doc_id", "")).lower()
            for doc in held
            if isinstance(doc, dict)
        }

        # Do not invent requirements for unsupported life events.
        if event_type != "relocation_interstate":
            return response([])

        if not from_state or not to_state or from_state == to_state:
            return response([])

        # These are demo checklist suggestions. The official authority
        # must be checked for the user's actual circumstances.
        candidates = [
            {
                "doc_id": "aadhaar",
                "service_id": "aadhaar_address_update",
                "priority": "mandatory",
                "reason": (
                    "Review your Aadhaar address after moving. "
                    "Other services may use it as address proof."
                ),
            },
            {
                "doc_id": "voter_id",
                "service_id": "voter_shift",
                "priority": "mandatory",
                "reason": (
                    "Review your voter registration so it reflects "
                    "your new place of ordinary residence."
                ),
            },
            {
                "doc_id": "driving_licence",
                "service_id": "dl_address_change",
                "priority": "mandatory",
                "reason": (
                    "Check whether your driving licence address "
                    "needs updating with the issuing authority."
                ),
            },
            {
                "doc_id": "vehicle_rc",
                "service_id": "vehicle_reregistration",
                "priority": "mandatory",
                "reason": (
                    "Check the applicable requirements for a vehicle "
                    "being kept in another state."
                ),
            },
            {
                "doc_id": "bank_account",
                "service_id": "bank_kyc_update",
                "priority": "recommended",
                "reason": (
                    "Update your bank's address records if needed "
                    "so correspondence and KYC details stay current."
                ),
            },
        ]

        result = []

        for item in candidates:
            result.append({
                **item,
                "held": item["doc_id"] in held_ids,
            })

        return response(result)

    except Exception as exc:
        return error_response(exc)


@mcp.tool()
def get_update_order(doc_ids: list[str]) -> dict:
    """
    Return a suggested order for reviewing relocation-related updates.

    The backend expects a list of document ID strings.
    """

    priority = {
        "aadhaar": 1,
        "voter_id": 2,
        "driving_licence": 3,
        "vehicle_rc": 4,
        "ration_card": 5,
        "passport": 6,
        "pan": 7,
        "bank_account": 8,
        "birth_certificate": 9,
        "pension_ppo": 10,
    }

    ordered = sorted(
        dict.fromkeys(doc_ids),
        key=lambda doc_id: priority.get(
            str(doc_id).lower(),
            99,
        ),
    )

    return response(ordered)


@mcp.tool()
def get_required_docs(
    service_id: str,
    state: str,
) -> dict:
    """Return known demo document requirements for a service."""

    requirements = {
        "voter_shift": ["aadhaar"],
        "aadhaar_address_update": [],
        "dl_address_change": [],
        "dl_renewal": [],
        "vehicle_reregistration": [],
        "bank_kyc_update": [],
    }

    if service_id not in requirements:
        return response([])

    return response(requirements[service_id])


@mcp.tool()
def get_alternatives(
    doc_id: str,
    purpose: str,
) -> dict:
    """
    Return known alternative documents for a purpose.

    No alternatives are currently configured in this prototype.
    """

    return response([])


@mcp.tool()
async def analyse_uploaded_document_text(text: str) -> dict:
    """
    Send OCR text to the Services MCP analysis tool.

    The receiving service is responsible for its own analysis.
    """

    try:
        result = await call_service_tool(
            "analyse_document_text",
            {"text": text},
        )

        return response(result)

    except Exception as exc:
        return error_response(exc)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
