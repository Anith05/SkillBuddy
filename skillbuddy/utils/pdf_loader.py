"""Utilities for extracting text from uploaded PDF resumes."""
from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader


def extract_text_from_pdf(buffer: BytesIO) -> str:
    """Return concatenated text from all pages in the PDF buffer."""
    reader = PdfReader(buffer)
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages)
