from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from docx import Document


def extract_pdf(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))

    pages = []

    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        pages.append(
            f"\n\n===== PAGE {index} =====\n{text}"
        )

    return "".join(pages)


def extract_docx(data: bytes) -> str:
    document = Document(BytesIO(data))

    paragraphs = []

    for index, paragraph in enumerate(document.paragraphs, start=1):
        text = paragraph.text.strip()

        if text:
            paragraphs.append(
                f"[PARAGRAPH {index}] {text}"
            )

    return "\n".join(paragraphs)


def extract_txt(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")


def extract_document(filename: str, data: bytes) -> str:
    extension = Path(filename).suffix.lower()

    if extension == ".pdf":
        return extract_pdf(data)

    if extension == ".docx":
        return extract_docx(data)

    if extension in [".txt", ".md"]:
        return extract_txt(data)

    raise ValueError(
        "Unsupported file type. Please upload PDF, DOCX, TXT or MD."
    )