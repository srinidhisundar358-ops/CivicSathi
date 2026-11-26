import base64
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from shared.ports import FORMFILL
from shared.schemas import PrefilledForm, ToolResult

from p2_documents.formfill_mcp.generator import (
    prefill_form as prefill_form_generator,
    validate_form,
    generate_pdf,
)

from p2_documents.formfill_mcp.service_client import call_service_tool


mcp = FastMCP(
    "formfill",
    host="0.0.0.0",
    port=FORMFILL,
)

# Resolve generated/ relative to the repository root, not the
# terminal's current working directory.
REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATED_DIR = REPO_ROOT / "generated"

SAFE_FORM_ID = re.compile(r"^[A-Za-z0-9_-]+$")


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
    """Check Form-fill MCP health."""
    return response("pong")


@mcp.tool()
def list_forms(
    service_id: str,
    state: str,
) -> dict:
    """List available preparation templates for a service."""

    template = {
        "voter_shift": {
            "service_id": "voter_shift",
            "state": "any",
            "form_name": "Voter shift",
            "official_link": "https://voters.eci.gov.in/",
        }
    }

    if service_id not in template:
        return response([])

    return response([template[service_id]])


@mcp.tool()
async def prepare_government_form(
    profile: dict,
    service_id: str,
) -> dict:
    """
    Ask the Services MCP to map a profile to form fields.

    This tool is retained for compatibility with the earlier prototype.
    """

    try:
        result = await call_service_tool(
            "map_profile_to_fields",
            {
                "profile": profile,
                "service_id": service_id,
            },
        )

        return response(result)

    except Exception as exc:
        return error_response(exc)


@mcp.tool()
def prefill_form(
    service_id: str,
    state: str,
    profile: dict,
) -> dict:
    """
    Prefill a supported form using profile data.

    Input names and output structure match the P1 backend contract.
    """

    try:
        draft = prefill_form_generator(
            profile=profile,
            service_id=service_id,
            state=state,
        )

        # Validate against the exact shared Pydantic schema.
        validated = PrefilledForm.model_validate(draft)

        return response(
            validated.model_dump(mode="json")
        )

    except Exception as exc:
        return error_response(exc)


@mcp.tool()
def list_missing_fields(form: dict) -> dict:
    """Return the fields that still need user input."""

    try:
        validated = PrefilledForm.model_validate(form)

        missing = [
            field.field_id
            for field in validated.fields
            if field.needs_user_input
        ]

        return response(missing)

    except Exception as exc:
        return error_response(exc)


@mcp.tool()
def validate_government_form(form_data: dict) -> dict:
    """Validate user-reviewed form data."""

    try:
        return response(validate_form(form_data))
    except Exception as exc:
        return error_response(exc)


@mcp.tool()
def generate_application_draft(form_data: dict) -> dict:
    """
    Generate a base64 PDF preparation draft.

    This is not an official government application.
    """

    try:
        validation = validate_form(form_data)
        pdf_base64 = generate_pdf(form_data)

        return response({
            "pdf_filename": (
                str(form_data.get("form_id", "application"))
                + ".pdf"
            ),
            "pdf_base64": pdf_base64,
            "validation": validation,
            "official_submission": False,
            "requires_user_review": True,
        })

    except Exception as exc:
        return error_response(exc)


@mcp.tool()
def render_form_pdf(form: dict) -> dict:
    """
    Generate and save a reviewable PDF in the repository's generated/
    directory.

    The P1 backend expects:
      {"pdf_path": "./generated/name.pdf", "file_name": "name.pdf"}
    """

    try:
        validated = PrefilledForm.model_validate(form)
        form_data = validated.model_dump(mode="json")

        form_id = validated.form_id

        if not SAFE_FORM_ID.fullmatch(form_id):
            raise ValueError("Invalid form_id.")

        GENERATED_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        pdf_base64 = generate_pdf(form_data)
        pdf_bytes = base64.b64decode(
            pdf_base64,
            validate=True,
        )

        filename = f"{form_id}.pdf"
        output_path = GENERATED_DIR / filename

        # Resolve and verify the path before writing.
        resolved_output = output_path.resolve()

        if resolved_output.parent != GENERATED_DIR.resolve():
            raise ValueError("Invalid PDF output path.")

        resolved_output.write_bytes(pdf_bytes)

        return response({
            "pdf_path": f"./generated/{filename}",
            "file_name": filename,
        })

    except Exception as exc:
        return error_response(exc)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
