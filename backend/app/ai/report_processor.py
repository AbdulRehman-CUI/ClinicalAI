"""Utilities for extracting text from uploaded medical reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document as DocxDocument
from pypdf import PdfReader


class ReportProcessor:
    """Extract plain text from supported medical report formats."""

    supported_extensions = {"PDF", "DOCX", "TXT"}

    def extract_text(self, file_path: str | Path) -> str:
        """Return normalized text for the supplied report file."""
        path = Path(file_path)
        suffix = path.suffix.upper().lstrip(".")
        if suffix == "PDF":
            return self._extract_from_pdf(path)
        if suffix == "DOCX":
            return self._extract_from_docx(path)
        if suffix == "TXT":
            return self._extract_from_txt(path)
        raise ValueError(f"Unsupported report type: {suffix}")

    def _extract_from_pdf(self, file_path: Path) -> str:
        try:
            reader = PdfReader(str(file_path))
        except Exception:
            return ""

        texts: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            page_text = self._normalize_text(page_text)
            if page_text:
                texts.append(page_text)
        return "\n\n".join(texts)

    def _extract_from_docx(self, file_path: Path) -> str:
        try:
            document = DocxDocument(str(file_path))
        except Exception:
            return ""
        paragraphs = [self._normalize_text(paragraph.text) for paragraph in document.paragraphs]
        return "\n".join(paragraph for paragraph in paragraphs if paragraph)

    def _extract_from_txt(self, file_path: Path) -> str:
        try:
            return self._normalize_text(file_path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            return self._normalize_text(file_path.read_text(encoding="latin-1"))
        except Exception:
            return ""

    def _normalize_text(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())
