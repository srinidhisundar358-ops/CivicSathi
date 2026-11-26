
from mcp.server.fastmcp import FastMCP

from shared.ports import DOCUMENTS
from shared.schemas import ToolResult

from p2_documents.documents_mcp.processor import (
    process_document
)

mcp = FastMCP(
    "documents",
    host="0.0.0.0",
    port=DOCUMENTS
)


def response(data):
    return ToolResult(
        ok=True,
        data=data,
        simulated=False
    ).model_dump(mode="json")


@mcp.tool()
def ping() -> dict:
    return response("pong")


@mcp.tool()
def upload_and_process_document(
    filename: str,
    content_base64: str
) -> dict:
    """
    Accept a PDF/image in base64 format.
    Extract text, detect document type and redact
    sensitive identity numbers in returned text.
    """

    try:
        result = process_document(
            filename,
            content_base64
        )

        return response(result)

    except Exception as exc:
        return ToolResult(
            ok=False,
            error=str(exc)
        ).model_dump(mode="json")


@mcp.tool()
def identify_document(text: str) -> dict:
    """
    Identify a document type from OCR-extracted text.
    """

    from p2_documents.documents_mcp.processor import (
        classify_document
    )

    return response(
        classify_document(text)
    )
@mcp.tool()
def get_affected_documents(
    from_state: str,
    to_state: str,
    documents: list[dict]
) -> dict:
    """
    Identify held documents that may need review after relocation.
    This flags state/address mismatches; it does not confirm
    that a government update is legally required.
    """

    affected = []

    for doc in documents:
        issued_state = doc.get("issued_state")
        address_state = doc.get("address_state")

        reasons = []

        if address_state and address_state.lower() != to_state.lower():
            reasons.append("Recorded address state differs from destination.")

        if issued_state and issued_state.lower() != to_state.lower():
            reasons.append("Document was issued in a different state; check portability or update rules.")

        if reasons:
            affected.append({
                "doc_id": doc.get("doc_id"),
                "issued_state": issued_state,
                "address_state": address_state,
                "reasons": reasons,
                "requires_official_verification": True
            })

    return response({
        "from_state": from_state,
        "to_state": to_state,
        "affected_documents": affected,
        "count": len(affected)
    })


@mcp.tool()
def get_update_order(
    affected_documents: list[dict]
) -> dict:
    """
    Suggest a practical review order for relocation-related updates.
    This is a recommendation, not an official government sequence.
    """

    priority = {
        "aadhaar": 1,
        "voter_id": 2,
        "ration_card": 3,
        "driving_licence": 4,
        "pan": 5,
        "passport": 6
    }

    ordered = sorted(
        affected_documents,
        key=lambda doc: priority.get(
            doc.get("doc_id", "").lower(),
            99
        )
    )

    return response({
        "recommended_update_order": ordered,
        "note": (
            "Suggested review order only. Verify each document's "
            "current requirements with its official issuing authority."
        )
    })

if __name__ == "__main__":
    mcp.run(transport="streamable-http")

from p2_documents.formfill_mcp.service_client import call_service_tool


@mcp.tool()
async def analyse_uploaded_document_text(text: str) -> dict:

    try:

        # Ask Person 3 to analyse OCR text.
        result = await call_service_tool(
            "analyse_document_text",
            {
                "text": text
            }
        )

        return response(result)

    except Exception as exc:

        return ToolResult(
            ok=False,
            error=str(exc)
        ).model_dump(mode="json")

