"""Versioned API route for document extraction and Gemini summarisation."""

import tempfile
import time
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from services.document_processor import DocumentExtractionError, extract_document_text
from services.file_validation import FileTooLargeError, UnsupportedFileTypeError, UploadValidationError, validate_upload
from services.gemini_service import (
    GeminiRateLimitError,
    GeminiRequestTimeoutError,
    GeminiService,
    GeminiServiceError,
    GeminiServiceUnavailableError,
)
from services.local_summarizer import LocalSummaryError, summarize_notice as summarize_locally


summarize_bp = Blueprint('summarize', __name__)


@summarize_bp.post('/api/v1/summarize')
def summarize_document():
    """Validate, extract, and summarise one supported college-notice document."""
    started_at = time.monotonic()
    upload = request.files.get('file')
    if upload is None or not upload.filename:
        return _error('A document file is required.', 400)

    filename = secure_filename(upload.filename)
    if not filename:
        return _error('The uploaded file name is invalid.', 400)

    try:
        data = upload.read()
        validated = validate_upload(filename, data)
        current_app.logger.info(
            'Upload received: filename=%s file_type=%s size_bytes=%d',
            filename, validated.file_type, len(data),
        )
        gemini = GeminiService(
            current_app.config['GEMINI_API_KEY'],
            current_app.config['GEMINI_MODEL'],
            timeout_ms=current_app.config['GEMINI_REQUEST_TIMEOUT_MS'],
            retry_attempts=current_app.config['GEMINI_RETRY_ATTEMPTS'],
        )
        with tempfile.TemporaryDirectory(prefix='college-notice-') as temporary_directory:
            file_path = Path(temporary_directory, filename)
            file_path.write_bytes(data)
            current_app.logger.info('Document extraction started: filename=%s file_type=%s', filename, validated.file_type)
            extracted_text, source_information, warnings = extract_document_text(
                file_path, validated.file_type, validated.mime_type, gemini,
            )
        current_app.logger.info(
            'Document extraction completed: filename=%s duration_seconds=%.3f',
            filename, time.monotonic() - started_at,
        )
        current_app.logger.info('Gemini summarisation started: filename=%s', filename)
        if not extracted_text.strip():
            raise DocumentExtractionError('No readable text was found in this document.')
        try:
            summary = gemini.summarize_notice(extracted_text, source_information, warnings)
            summary_mode = 'ai'
            warning = None
        except (GeminiRateLimitError, GeminiRequestTimeoutError, GeminiServiceUnavailableError) as error:
            current_app.logger.warning('Gemini summary unavailable; using local fallback: filename=%s', filename)
            summary = summarize_locally(extracted_text, source_information, warnings)
            summary_mode = 'local'
            warning = 'AI summarisation is temporarily unavailable; a local summary was generated from the extracted text.'
        current_app.logger.info(
            'Gemini summarisation completed: filename=%s total_duration_seconds=%.3f',
            filename, time.monotonic() - started_at,
        )
    except FileTooLargeError as error:
        return _error(str(error), 413)
    except UnsupportedFileTypeError as error:
        return _error(str(error), 415)
    except (UploadValidationError, DocumentExtractionError, LocalSummaryError) as error:
        return _error(str(error), 400)
    except GeminiServiceError as error:
        current_app.logger.warning(
            'Document processing failed: filename=%s http_status=%d total_duration_seconds=%.3f',
            filename, error.status_code, time.monotonic() - started_at,
        )
        return _error(str(error), error.status_code)

    return jsonify({
        'success': True,
        'filename': filename,
        'file_type': validated.file_type,
        'extracted_text': extracted_text,
        'summary': summary,
        'summary_mode': summary_mode,
        **({'warning': warning} if warning else {}),
    }), 200


def _error(message: str, status_code: int):
    return jsonify({'success': False, 'message': message, 'status': 'error'}), status_code
