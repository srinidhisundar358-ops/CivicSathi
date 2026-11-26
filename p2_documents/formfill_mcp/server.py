
from mcp.server.fastmcp import FastMCP

from shared.ports import FORMFILL
from shared.schemas import ToolResult

from p2_documents.formfill_mcp.generator import (
    prefill_form,
    validate_form,
    generate_pdf
)

mcp = FastMCP(
    "formfill",
    host="0.0.0.0",
    port=FORMFILL
)


def response(data):
    return ToolResult(
        ok=True,
        data=data,
        simulated=False
    ).model_dump(mode="json")


@mcp.tool()
def ping() -> dict:
    """Check Form-fill MCP health."""

    return response("pong")



from p2_documents.formfill_mcp.service_client import call_service_tool


@mcp.tool()
async def prepare_government_form(
    profile: dict,
    service_id: str
) -> dict:

    try:

        result = await call_service_tool(
            "map_profile_to_fields",
            {
                "profile": profile,
                "service_id": service_id
            }
        )

        return response(result)

    except Exception as exc:

        return ToolResult(
            ok=False,
            error=str(exc)
        ).model_dump(mode="json")



@mcp.tool()
def validate_government_form(
    form_data: dict
) -> dict:
    """
    Validate citizen-reviewed form information.
    """

    return response(
        validate_form(form_data)
    )


@mcp.tool()
def generate_application_draft(
    form_data: dict
) -> dict:
    """
    Generate a PDF preparation draft.
    Returns base64 PDF content.
    """

    try:
        validation = validate_form(form_data)

        pdf_base64 = generate_pdf(form_data)

        return response({
            "pdf_filename": (
                form_data.get("form_id", "application")
                + "_draft.pdf"
            ),
            "pdf_base64": pdf_base64,
            "validation": validation,
            "official_submission": False,
            "requires_user_review": True
        })

    except Exception as exc:
        return ToolResult(
            ok=False,
            error=str(exc)
        ).model_dump(mode="json")


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
