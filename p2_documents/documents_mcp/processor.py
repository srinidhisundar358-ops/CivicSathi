
import base64
import io
import re
from pathlib import Path

import fitz
import pytesseract

from PIL import Image, ImageOps


# If Tesseract is not in PATH, uncomment and edit:
# pytesseract.pytesseract.tesseract_cmd = (
#     r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# )

MAX_FILE_SIZE = 8 * 1024 * 1024

SUPPORTED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg"
}


DOCUMENT_KEYWORDS = {
    "aadhaar": [
        "aadhaar",
        "unique identification authority"
    ],
    "pan": [
        "permanent account number",
        "income tax department"
    ],
    "voter_id": [
        "election commission",
        "elector photo identity"
    ],
    "driving_licence": [
        "driving licence",
        "driving license"
    ],
    "passport": [
        "passport",
        "republic of india"
    ],
    "ration_card": [
        "ration card",
        "public distribution system"
    ],
    "birth_certificate": [
        "birth certificate",
        "date of birth"
    ]
}


def decode_file(filename, content_base64):

    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file format.")

    try:
        content = base64.b64decode(
            content_base64,
            validate=True
        )
    except Exception:
        raise ValueError("Invalid base64 file content.")

    if not content or len(content) > MAX_FILE_SIZE:
        raise ValueError("File is empty or exceeds 8 MB.")

    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise ValueError("Invalid PDF file.")

    if extension in {".png", ".jpg", ".jpeg"}:
        try:
            image = Image.open(io.BytesIO(content))
            image.verify()
        except Exception:
            raise ValueError("Invalid image file.")

    return content, extension


def redact_identity_numbers(text):

    # Aadhaar-like 12 digit sequences
    text = re.sub(
        r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        "[REDACTED ID NUMBER]",
        text
    )

    # PAN-like patterns
    text = re.sub(
        r"\b[A-Z]{5}\d{4}[A-Z]\b",
        "[REDACTED ID NUMBER]",
        text,
        flags=re.IGNORECASE
    )

    return text


def extract_pdf_text(content):

    document = fitz.open(
        stream=content,
        filetype="pdf"
    )

    if document.page_count > 10:
        document.close()
        raise ValueError("Maximum 10 PDF pages allowed.")

    pages = []

    try:
        for page in document:
            text = page.get_text()

            # OCR scanned pages when text is unavailable
            if not text.strip():

                pixmap = page.get_pixmap(
                    matrix=fitz.Matrix(2, 2),
                    alpha=False
                )

                image = Image.open(
                    io.BytesIO(pixmap.tobytes("png"))
                )

                text = pytesseract.image_to_string(
                    image,
                    lang="eng"
                )

            pages.append(text)

        return "\n".join(pages)

    finally:
        document.close()


def extract_image_text(content):

    image = Image.open(
        io.BytesIO(content)
    )

    image = ImageOps.grayscale(image)

    return pytesseract.image_to_string(
        image,
        lang="eng"
    )


def classify_document(text):

    normalised = text.lower()

    scores = {}

    for document_type, keywords in DOCUMENT_KEYWORDS.items():

        score = sum(
            1 for keyword in keywords
            if keyword in normalised
        )

        if score:
            scores[document_type] = score

    if not scores:
        return {
            "document_type": "unknown",
            "confidence": "low",
            "requires_confirmation": True
        }

    best = max(scores, key=scores.get)

    return {
        "document_type": best,
        "confidence": (
            "medium" if scores[best] == 1 else "high"
        ),
        "requires_confirmation": True
    }


def process_document(filename, content_base64):

    content, extension = decode_file(
        filename,
        content_base64
    )

    if extension == ".pdf":
        extracted_text = extract_pdf_text(content)
    else:
        extracted_text = extract_image_text(content)

    if not extracted_text.strip():
        return {
            "success": False,
            "message": "No readable text found."
        }

    classification = classify_document(
        extracted_text
    )

    safe_text = redact_identity_numbers(
        extracted_text
    )

    return {
        "success": True,
        "filename": Path(filename).name,
        "document_type": classification["document_type"],
        "confidence": classification["confidence"],
        "requires_confirmation": True,
        "extracted_text": safe_text,
        "sensitive_numbers_redacted": True,
        "stored_permanently": False
    }
