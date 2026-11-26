import base64
import io
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


FORM_TEMPLATES = {
    "voter_shift": {
        "name": "Voter Registration / Shifting Preparation",
        "official_link": "https://voters.eci.gov.in/",
    },
}


def get_value(data, path):
    """Safely read a nested profile value."""

    if not path:
        return None

    current = data

    for key in path.split("."):
        if not isinstance(current, dict):
            return None

        current = current.get(key)

    if current is None:
        return None

    value = str(current).strip()

    return value if value else None


def prefill_form(profile, service_id, state):
    """
    Map the user's profile to the supported form template.

    The returned dictionary follows shared.schemas.PrefilledForm.
    """

    template = FORM_TEMPLATES.get(service_id)

    if template is None:
        raise ValueError(
            f"Unsupported form template: {service_id}"
        )

    if not isinstance(profile, dict):
        raise ValueError("Profile must be a dictionary.")

    user_id = profile.get("user_id")

    if not user_id:
        raise ValueError("Profile is missing user_id.")

    fields_to_map = [
        {
            "field_id": "full_name",
            "label": "Full name",
            "path": "personal.full_name",
            "required": True,
        },
        {
            "field_id": "relative_name",
            "label": "Father / relative name",
            "path": "personal.relative_name",
            "required": False,
        },
        {
            "field_id": "dob",
            "label": "Date of birth",
            "path": "personal.dob",
            "required": False,
        },
        {
            "field_id": "phone",
            "label": "Mobile number",
            "path": "personal.phone",
            "required": False,
        },
        {
            "field_id": "email",
            "label": "Email address",
            "path": "personal.email",
            "required": False,
        },
        {
            "field_id": "address_line1",
            "label": "House number and street",
            "path": "personal.address.line1",
            "required": True,
        },
        {
            "field_id": "city",
            "label": "City",
            "path": "personal.address.city",
            "required": True,
        },
        {
            "field_id": "district",
            "label": "District",
            "path": "personal.address.district",
            "required": False,
        },
        {
            "field_id": "state",
            "label": "Destination state",
            "path": None,
            "required": True,
        },
        {
            "field_id": "pincode",
            "label": "PIN code",
            "path": "personal.address.pincode",
            "required": True,
        },
        {
            "field_id": "epic_number",
            "label": "EPIC number",
            "path": None,
            "required": True,
        },
    ]

    fields = []
    missing = []

    for definition in fields_to_map:
        field_id = definition["field_id"]

        if field_id == "state":
            value = state.strip() if state else None
        else:
            value = get_value(
                profile,
                definition["path"],
            )

        # EPIC number is deliberately not read from the profile.
        # The user must enter and verify it themselves.
        needs_user_input = (
            definition["required"]
            and not value
        )

        if needs_user_input:
            missing.append(field_id)

        fields.append({
            "field_id": field_id,
            "label": definition["label"],
            "value": value,
            "source": "profile" if value else "user",
            "required": definition["required"],
            "needs_user_input": needs_user_input,
        })

    return {
        "form_id": f"demo_{service_id}",
        "user_id": user_id,
        "service_id": service_id,
        "state": state,
        "fields": fields,
        "missing": missing,
        "official_link": template["official_link"],
        "status": "draft",
    }


def validate_form(form_data):
    """Validate required fields and basic PIN-code formatting."""

    errors = []
    missing = []

    for field in form_data.get("fields", []):
        field_id = field.get("field_id")
        value = field.get("value")

        if field.get("required") and (
            value is None or str(value).strip() == ""
        ):
            missing.append(field_id)

        if field_id == "pincode" and value:
            if not re.fullmatch(r"\d{6}", str(value).strip()):
                errors.append(
                    "PIN code must contain exactly 6 digits."
                )

    return {
        "valid": not errors and not missing,
        "errors": errors,
        "missing": missing,
        "requires_user_approval": True,
    }


def generate_pdf(form_data):
    """
    Generate a non-official review PDF.

    The PDF is a preparation document only. It is not a government
    application and is never submitted automatically.
    """

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CivicTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#263B60"),
    )

    warning_style = ParagraphStyle(
        "CivicWarning",
        parent=styles["Normal"],
        textColor=colors.HexColor("#9B2C2C"),
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )

    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
    )

    elements = [
        Paragraph("CIVICSAATHI", title_style),
        Spacer(1, 5 * mm),
        Paragraph(
            "Government Application Preparation Draft",
            styles["Heading2"],
        ),
        Spacer(1, 3 * mm),
        Paragraph(
            "NOT AN OFFICIAL GOVERNMENT FORM",
            warning_style,
        ),
        Spacer(1, 7 * mm),
    ]

    service_name = FORM_TEMPLATES.get(
        form_data.get("service_id"),
        {},
    ).get(
        "name",
        form_data.get("service_id", "Application"),
    )

    elements.append(
        Paragraph(
            f"<b>Service:</b> {escape(str(service_name))}",
            styles["Normal"],
        )
    )

    elements.append(
        Paragraph(
            f"<b>State:</b> "
            f"{escape(str(form_data.get('state') or 'Not provided'))}",
            styles["Normal"],
        )
    )

    elements.append(Spacer(1, 5 * mm))

    table_data = [
        [
            Paragraph("<b>Field</b>", cell_style),
            Paragraph("<b>Value</b>", cell_style),
            Paragraph("<b>Status</b>", cell_style),
        ]
    ]

    for field in form_data.get("fields", []):
        value = field.get("value")
        label = field.get("label", field.get("field_id", "Field"))

        if field.get("needs_user_input") or not value:
            status = "Needs user input"
        else:
            status = "Prefilled - verify"

        table_data.append([
            Paragraph(escape(str(label)), cell_style),
            Paragraph(
                escape(str(value)) if value else "Not provided",
                cell_style,
            ),
            Paragraph(status, cell_style),
        ])

    table = Table(
        table_data,
        colWidths=[48 * mm, 78 * mm, 42 * mm],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#DDE6F5"),
            ),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    elements.append(table)
    elements.append(Spacer(1, 7 * mm))

    missing = form_data.get("missing", [])

    elements.append(
        Paragraph(
            "Information still required",
            styles["Heading3"],
        )
    )

    if missing:
        for field_id in missing:
            elements.append(
                Paragraph(
                    f"- {escape(str(field_id))}",
                    styles["Normal"],
                )
            )
    else:
        elements.append(
            Paragraph(
                "No required fields are currently missing.",
                styles["Normal"],
            )
        )

    elements.append(Spacer(1, 7 * mm))

    official_link = form_data.get("official_link", "")

    elements.append(
        Paragraph(
            f"<b>Official portal:</b> {escape(str(official_link))}",
            styles["Normal"],
        )
    )

    elements.append(Spacer(1, 5 * mm))

    elements.append(
        Paragraph(
            "Please verify every detail against your original "
            "documents and the official government portal. "
            "Complete and submit the actual application yourself "
            "through the official portal.",
            styles["Italic"],
        )
    )

    document.build(elements)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return base64.b64encode(pdf_bytes).decode("utf-8")
