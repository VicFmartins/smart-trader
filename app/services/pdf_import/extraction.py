from __future__ import annotations

import io
from dataclasses import dataclass

from app.core.exceptions import DocumentImportError
from app.schemas.pdf_import import PDFExtractionMetadata, PDFPageText


@dataclass(frozen=True, slots=True)
class PDFExtractionResult:
    pages: list[PDFPageText]
    combined_text: str
    metadata: PDFExtractionMetadata


class PDFTextExtractor:
    def __init__(self, *, max_pages: int, max_chars: int) -> None:
        self.max_pages = max_pages
        self.max_chars = max_chars

    def extract(self, file_bytes: bytes) -> PDFExtractionResult:
        extraction_errors: list[str] = []
        pages: list[PDFPageText] = []
        extractor_used = ""

        try:
            pages, extractor_used = self._extract_with_pdfplumber(file_bytes)
        except DocumentImportError as exc:
            extraction_errors.append(str(exc))

        if not any(page.text.strip() for page in pages):
            try:
                pages, extractor_used = self._extract_with_pymupdf(file_bytes)
            except DocumentImportError as exc:
                extraction_errors.append(str(exc))

        if not pages:
            message = "No pages could be extracted from the uploaded PDF."
            if extraction_errors:
                message += " " + " | ".join(extraction_errors)
            raise DocumentImportError(message)

        combined_text = "\n\n".join(
            f"[PAGE {page.page_number}]\n{page.text}".strip()
            for page in pages
            if page.text.strip()
        )
        truncated_text = combined_text[: self.max_chars]
        text_truncated = len(truncated_text) < len(combined_text)

        return PDFExtractionResult(
            pages=pages,
            combined_text=truncated_text,
            metadata=PDFExtractionMetadata(
                extractor_used=extractor_used,
                page_count=len(pages),
                extracted_characters=len(truncated_text),
                text_truncated=text_truncated,
            ),
        )

    def _extract_with_pdfplumber(self, file_bytes: bytes) -> tuple[list[PDFPageText], str]:
        try:
            import pdfplumber
        except ImportError as exc:
            raise DocumentImportError("pdfplumber is not installed. Add it to the local environment.") from exc

        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages = []
                for index, page in enumerate(pdf.pages[: self.max_pages], start=1):
                    text = page.extract_text() or ""
                    pages.append(PDFPageText(page_number=index, text=text, char_count=len(text)))
                return pages, "pdfplumber"
        except Exception as exc:
            raise DocumentImportError("Failed to extract text from the PDF with pdfplumber.") from exc

    def _extract_with_pymupdf(self, file_bytes: bytes) -> tuple[list[PDFPageText], str]:
        try:
            import fitz
        except ImportError as exc:
            raise DocumentImportError("PyMuPDF is not installed. Add it to the local environment.") from exc

        try:
            document = fitz.open(stream=file_bytes, filetype="pdf")
            try:
                pages = []
                total_pages = min(document.page_count, self.max_pages)
                for index in range(total_pages):
                    page = document.load_page(index)
                    text = page.get_text("text") or ""
                    pages.append(PDFPageText(page_number=index + 1, text=text, char_count=len(text)))
                return pages, "pymupdf"
            finally:
                document.close()
        except Exception as exc:
            raise DocumentImportError("Failed to extract text from the PDF with PyMuPDF.") from exc
