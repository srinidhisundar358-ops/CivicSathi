
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


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
