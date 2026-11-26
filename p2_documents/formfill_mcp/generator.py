
import io
import base64
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)


# ------------------------------------------------
# GOVERNMENT FORM TEMPLATES
# ------------------------------------------------

FORM_TEMPLATES = {

    "voter_shift": {
        "name": "Voter Registration / Shifting Preparation",
        "state_specific": True,
        "official_link": "https://voters.eci.gov.in/",

        "fields": {
            "full_name": {
                "label": "Full Name",
                "source": "personal.full_name",
                "required": True,
                "help": "Enter your name as recorded in your identity documents."
            },

            "dob": {
                "label": "Date of Birth",
                "source": "personal.dob",
                "required": True,
                "help": "Enter your date of birth."
            },

            "address": {
                "label": "Current Address",
                "source": "personal.address.line1",
                "required": True,
                "help": "Enter your current residential address."
            },

            "city": {
                "label": "City",
                "source": "personal.address.city",
                "required": True,
                "help": "Enter your current city."
            },

            "state": {
                "label": "Current State",
                "source": "personal.address.state",
                "required": True,
                "help": "Select your current state of residence."
            },

            "pincode": {
                "label": "PIN Code",
                "source": "personal.address.pincode",
                "required": True,
                "help": "Enter the six-digit PIN code."
            },

            "epic_number": {
                "label": "EPIC Number",
                "source": None,
                "required": True,
                "help": "Enter the number printed on your Voter ID."
            }
        }
    },

    "aadhaar_address_update": {
        "name": "Aadhaar Address Update Preparation",
        "state_specific": False,
        "official_link": "https://uidai.gov.in/",

        "fields": {
            "full_name": {
                "label": "Full Name",
                "source": "personal.full_name",
                "required": True,
                "help": "Enter your name as recorded in Aadhaar."
            },

            "address": {
                "label": "New Address",
                "source": "personal.address.line1",
                "required": True,
                "help": "Enter your new residential address."
            },

            "city": {
                "label": "City",
                "source": "personal.address.city",
                "required": True,
                "help": "Enter your current city."
            },

            "state": {
                "label": "State",
                "source": "personal.address.state",
                "required": True,
                "help": "Enter your current state."
            },

            "pincode": {
                "label": "PIN Code",
                "source": "personal.address.pincode",
                "required": True,
                "help": "Enter your six-digit PIN code."
            }
        }
    },

    "dl_renewal": {
        "name": "Driving Licence Renewal Preparation",
        "state_specific": True,
        "official_link": "https://parivahan.gov.in/",

        "fields": {
            "full_name": {
                "label": "Applicant Name",
                "source": "personal.full_name",
                "required": True,
                "help": "Enter the name recorded on your driving licence."
            },

            "dob": {
                "label": "Date of Birth",
                "source": "personal.dob",
                "required": True,
                "help": "Enter your date of birth."
            },

            "address": {
                "label": "Current Address",
                "source": "personal.address.line1",
                "required": True,
                "help": "Enter your current residential address."
            }
        }
    }
}


# ------------------------------------------------
# HELPER FUNCTION
# ------------------------------------------------

def get_value(data, path):

    if not path:
        return None

    current = data

    for key in path.split("."):

        if not isinstance(current, dict):
            return None

        current = current.get(key)

    if current is None:
        return None

    return str(current).strip()


# ------------------------------------------------
# MAP PROFILE TO FORM
# ------------------------------------------------

def prefill_form(profile, service_id):

    template = FORM_TEMPLATES.get(service_id)

    if not template:
        raise ValueError("Unsupported form template.")

    fields = []
    missing = []

    for field_id, definition in template["fields"].items():

        value = get_value(
            profile,
            definition["source"]
        )

        needs_input = (
            value is None or value == ""
        )

        if needs_input and definition["required"]:
            missing.append(field_id)

        fields.append({
            "field_id": field_id,
            "label": definition["label"],
            "value": value,
            "required": definition["required"],
            "needs_user_input": needs_input,
            "source": (
                "profile" if not needs_input
                else "user"
            ),
            "help": definition["help"]
        })

    return {
        "form_id": service_id,
        "user_id": profile.get("user_id"),
        "service_name": template["name"],
        "fields": fields,
        "missing": missing,
        "official_link": template["official_link"],
        "status": "draft",
        "ready_for_review": len(missing) == 0
    }


# ------------------------------------------------
# VALIDATE USER-EDITED FIELDS
# ------------------------------------------------

def validate_form(form_data):

    errors = []
    missing = []

    for field in form_data.get("fields", []):

        field_id = field["field_id"]
        value = field.get("value")

        if field.get("required") and (
            value is None or str(value).strip() == ""
        ):
            missing.append(field_id)

        if field_id == "pincode" and value:

            if not re.fullmatch(r"\d{6}", str(value)):
                errors.append(
                    "PIN code must contain exactly 6 digits."
                )

    return {
        "valid": not errors and not missing,
        "errors": errors,
        "missing": missing,
        "requires_user_approval": True
    }


# ------------------------------------------------
# GENERATE PDF DRAFT
# ------------------------------------------------

def generate_pdf(form_data):

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            "CIVICSAATHI",
            styles["Title"]
        )
    )

    elements.append(
        Paragraph(
            "Government Application Preparation Draft",
            styles["Heading2"]
        )
    )

    elements.append(Spacer(1, 12))

    elements.append(
        Paragraph(
            "<b>NOT AN OFFICIAL GOVERNMENT FORM</b>",
            styles["Warning"]
            if "Warning" in styles
            else styles["Normal"]
        )
    )

    elements.append(Spacer(1, 15))

    elements.append(
        Paragraph(
            "Service: " + form_data.get("service_name", ""),
            styles["Heading3"]
        )
    )

    elements.append(Spacer(1, 10))

    table_data = [
        ["Field", "Value", "Status"]
    ]

    for field in form_data.get("fields", []):

        value = field.get("value")

        status = (
            "NEEDS INPUT"
            if field.get("needs_user_input") or not value
            else "PREFILLED - VERIFY"
        )

        table_data.append([
            field["label"],
            str(value) if value else "Not provided",
            status
        ])

    table = Table(
        table_data,
        colWidths=[125, 230, 110],
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE6F5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 7),
        ])
    )

    elements.append(table)

    elements.append(Spacer(1, 20))

    missing = form_data.get("missing", [])

    elements.append(
        Paragraph(
            "Information still required",
            styles["Heading3"]
        )
    )

    if missing:

        for field in missing:
            elements.append(
                Paragraph(
                    "• " + field,
                    styles["Normal"]
                )
            )

    else:

        elements.append(
            Paragraph(
                "No required fields are missing from the profile.",
                styles["Normal"]
            )
        )

    elements.append(Spacer(1, 20))

    elements.append(
        Paragraph(
            "Official Portal: " +
            form_data.get("official_link", ""),
            styles["Normal"]
        )
    )

    elements.append(Spacer(1, 15))

    elements.append(
        Paragraph(
            "Please verify all information against your original "
            "documents and the official government portal before "
            "submitting any application.",
            styles["Italic"]
        )
    )

    document.build(elements)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return base64.b64encode(pdf_bytes).decode("utf-8")
