import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from p1_core_backend.config import REPO_ROOT
from p1_core_backend.db import store
from shared.schemas import PrefilledForm


router = APIRouter()
GENERATED_DIR = REPO_ROOT / "generated"
PDF_NAME = re.compile(r"[A-Za-z0-9_-]+\.pdf")


@router.get("/forms/{form_id}", response_model=PrefilledForm)
def get_form(form_id: str) -> PrefilledForm:
    form = store.get_form(form_id)
    if form is None:
        raise HTTPException(status_code=404, detail="Form not found")
    return form


def _pdf_path(name: str) -> Path:
    if not PDF_NAME.fullmatch(name):
        raise HTTPException(status_code=404, detail="PDF not found")

    path = (GENERATED_DIR / name).resolve()
    if path.parent != GENERATED_DIR.resolve():
        raise HTTPException(status_code=404, detail="PDF not found")

    return path


def _write_demo_pdf(path: Path, form: PrefilledForm) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.drawString(50, 790, "CivicSaathi demo - voter-shift review")
    pdf.drawString(50, 765, "Complete these fields on the official portal:")

    y = 740
    for field in form.fields:
        if field.needs_user_input or field.field_id in form.missing:
            pdf.drawString(50, y, field.label)
            y -= 20

    pdf.drawString(50, y - 10, form.official_link)
    pdf.save()


@router.post("/forms/{form_id}/confirm")
async def confirm_form(form_id: str, request: Request) -> dict[str, str]:
    form = get_form(form_id)
    reviewed = form.model_copy(update={"status": "reviewed"})

    result = await request.app.state.mcp_hub.call(
        "formfill", "render_form_pdf", {"form": reviewed.model_dump(mode="json")}
    )
    if not result.ok:
        raise HTTPException(status_code=502, detail="Form PDF generation failed")

    if result.simulated:
        name = f"{form.form_id}.pdf"
        _write_demo_pdf(_pdf_path(name), reviewed)
    else:
        data = result.data if isinstance(result.data, dict) else {}
        name = data.get("file_name")
        if not isinstance(name, str) or not PDF_NAME.fullmatch(name):
            raise HTTPException(status_code=502, detail="Invalid form PDF filename")

    if not _pdf_path(name).is_file():
        raise HTTPException(status_code=502, detail="Generated PDF is missing")

    store.save_form(reviewed)
    return {"pdf_url": f"/files/{name}", "official_link": reviewed.official_link}


@router.get("/files/{name}", response_class=FileResponse)
def download_pdf(name: str) -> FileResponse:
    path = _pdf_path(name)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(path, media_type="application/pdf", filename=name)
EDITABLE_FIELDS = {
    "full_name",
    "relative_name",
    "dob",
    "phone",
    "email",
    "address_line1",
    "city",
    "district",
    "state",
    "pincode",
}


@router.put("/forms/{form_id}", response_model=PrefilledForm)
def update_form(form_id: str, body: PrefilledForm) -> PrefilledForm:
    saved = get_form(form_id)
    if body.form_id != form_id or body.user_id != saved.user_id:
        raise HTTPException(status_code=422, detail="Form identity does not match")
    if saved.status != "draft":
        raise HTTPException(status_code=409, detail="Only drafts can be edited")

    incoming = {field.field_id: field for field in body.fields}
    fields = []
    for field in saved.fields:
        edit = incoming.get(field.field_id)
        if edit is not None and field.field_id in EDITABLE_FIELDS:
            value = (edit.value or "").strip() or None
            if value != field.value:
                field = field.model_copy(update={
                    "value": value,
                    "source": "user",
                    "needs_user_input": field.required and value is None,
                })
        fields.append(field)

    updated = saved.model_copy(update={
        "fields": fields,
        "missing": [field.field_id for field in fields if field.needs_user_input],
    })
    store.save_form(updated)
    return updated