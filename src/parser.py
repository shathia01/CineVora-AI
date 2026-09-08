from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional

from docx import Document
from pypdf import PdfReader


@dataclass
class ParsedScript:
    text: str
    filename: str
    extension: str
    page_count: Optional[int] = None


def parse_uploaded_file(uploaded_file) -> ParsedScript:
    name = uploaded_file.name
    ext = Path(name).suffix.lower()
    data = uploaded_file.getvalue()

    if ext == ".pdf":
        reader = PdfReader(BytesIO(data))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return ParsedScript("\n\n".join(pages).strip(), name, ext, len(reader.pages))

    if ext == ".docx":
        doc = Document(BytesIO(data))
        text = "\n".join(p.text for p in doc.paragraphs)
        return ParsedScript(text.strip(), name, ext, None)

    if ext == ".txt":
        for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
            try:
                return ParsedScript(data.decode(encoding).strip(), name, ext, None)
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode this TXT file.")

    raise ValueError("Unsupported file type. Please upload PDF, DOCX, or TXT.")


def read_sample(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
