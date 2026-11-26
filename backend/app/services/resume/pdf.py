"""PDF text extraction.

We use **pypdf** (pure Python). PyMuPDF is faster but its compiled extensions
are blocked by Windows Application Control on this machine; pypdf is reliable,
dependency-light, and works for text-based (non-scanned) resumes.
"""

from io import BytesIO

from pypdf import PdfReader

MAX_PDF_PAGES = 50
MAX_PDF_TEXT_CHARS = 2_000_000


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be read or yields no text."""


def extract_text_from_pdf(data: bytes) -> str:
    if not data:
        raise PdfExtractionError("The uploaded file is empty")

    try:
        reader = PdfReader(BytesIO(data))

        if reader.is_encrypted:
            raise PdfExtractionError(
                "Password-protected PDFs are not supported. Please upload an unlocked PDF."
            )

        if len(reader.pages) == 0:
            raise PdfExtractionError("The PDF has no pages")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise PdfExtractionError(
                f"The PDF has too many pages (maximum is {MAX_PDF_PAGES})"
            )

        chunks: list[str] = []
        total_chars = 0
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
            except Exception:  # noqa: BLE001 - a single bad page must not kill the upload
                text = ""
            total_chars += len(text)
            if total_chars > MAX_PDF_TEXT_CHARS:
                raise PdfExtractionError(
                    "The PDF contains too much text to process safely"
                )
            chunks.append(text)
        return "\n".join(chunks)
    except PdfExtractionError:
        raise
    except Exception as exc:  # noqa: BLE001 - pypdf raises several error types
        raise PdfExtractionError(
            "Could not read the PDF. The file may be corrupted or unsupported."
        ) from exc
