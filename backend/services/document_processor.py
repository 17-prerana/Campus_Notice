"""Extracts text from PDFs and images without combining extraction with summarisation."""

from pathlib import Path

import fitz

from services.gemini_service import GeminiService


class DocumentExtractionError(ValueError):
    """Raised when a document cannot yield readable notice text."""


def extract_document_text(file_path: Path, file_type: str, mime_type: str, gemini: GeminiService) -> tuple[str, str, list[str]]:
    """Return extracted text, source information, and OCR uncertainty warnings."""
    if file_type == 'image':
        text = gemini.extract_text_from_image(file_path.read_bytes(), mime_type, file_path.name)
        return text, 'Text extracted with Gemini vision OCR from an uploaded image.', _ocr_warnings(text)
    return _extract_pdf_text(file_path, gemini)


def _extract_pdf_text(file_path: Path, gemini: GeminiService) -> tuple[str, str, list[str]]:
    try:
        document = fitz.open(file_path)
    except (fitz.FileDataError, RuntimeError) as error:
        raise DocumentExtractionError('The PDF could not be opened.') from error

    try:
        pages = [page.get_text('text').strip() for page in document]
        extracted = '\n\n'.join(f'[Page {index + 1}]\n{text}' for index, text in enumerate(pages) if text)
        if extracted:
            return extracted, f'Text extracted directly from a {len(pages)}-page PDF.', []

        ocr_pages = []
        for index, page in enumerate(document):
            image_data = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes('png')
            page_text = gemini.extract_text_from_image(image_data, 'image/png', f'{file_path.name}, page {index + 1}')
            ocr_pages.append(f'[Page {index + 1}]\n{page_text}')
        text = '\n\n'.join(ocr_pages).strip()
        if not text:
            raise DocumentExtractionError('No readable text was found in this PDF.')
        warnings = _ocr_warnings(text)
        warnings.insert(0, 'This scanned PDF was transcribed with vision OCR; verify critical details against the original document.')
        return text, f'Text extracted with Gemini vision OCR from a scanned {len(pages)}-page PDF.', warnings
    finally:
        document.close()


def _ocr_warnings(text: str) -> list[str]:
    return ['OCR contains one or more unclear sections.'] if '[unclear]' in text.lower() or '[unreadable]' in text.lower() else []
