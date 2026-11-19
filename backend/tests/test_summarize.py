"""Route tests for upload validation and safe Gemini failure handling."""

import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from app import create_app
from services.document_processor import extract_document_text
import httpx

from services.gemini_service import (
    GeminiAuthenticationError,
    GeminiModelNotFoundError,
    GeminiRateLimitError,
    GeminiRequestTimeoutError,
    GeminiService,
    GeminiServiceUnavailableError,
)
from services.local_summarizer import NOT_MENTIONED, summarize_notice as summarize_locally


def text_pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), 'Exam notice: submit the form by 20 December 2026.')
    data = document.tobytes()
    document.close()
    return data


def image_bytes(kind: str) -> bytes:
    # Signatures are enough for route validation; Gemini extraction is mocked below.
    return b'\xff\xd8\xff\xe0test' if kind == 'jpeg' else b'\x89PNG\r\n\x1a\nimage'


SUMMARY = {
    'short_summary': 'Exam form deadline',
    'detailed_summary': 'Students must submit the exam form by 20 December 2026.',
    'important_dates': ['20 December 2026'],
    'target_audience': 'Students',
    'department': 'Examination Cell',
    'urgency': 'High',
    'action_items': ['Submit the form'],
    'important_instructions': ['Use the prescribed form'],
    'source_information': 'ignored by route mock',
    'uncertainty_warnings': [],
}

NOTICE_TEXT = '''COLLEGE NOTICE: Annual Science Seminar
All final-year B.Sc. students are eligible to attend the Annual Science Seminar.
The seminar will be held on 20 December 2026 at the Main Auditorium.
Students must register by 15 December 2026 and submit their college ID card copy.
For assistance, contact the Science Department at science@example.edu.
'''


class SummarizeRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, GEMINI_API_KEY='test-key', GEMINI_MODEL='test-model')
        self.client = self.app.test_client()

    def post_file(self, data: bytes, filename: str):
        return self.client.post('/api/v1/summarize', data={'file': (io.BytesIO(data), filename)})

    def test_health_check(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'healthy')
        self.assertTrue(response.json['success'])

    @patch('routes.summarize.extract_document_text')
    @patch('routes.summarize.GeminiService')
    def test_text_pdf_returns_summary(self, gemini_class, extract_text):
        gemini_class.return_value.summarize_notice.return_value = SUMMARY
        extract_text.return_value = ('Exam notice', 'Direct PDF text.', [])
        response = self.post_file(text_pdf_bytes(), 'exam_notice.pdf')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['success'])
        self.assertEqual(response.json['filename'], 'exam_notice.pdf')
        self.assertEqual(response.json['file_type'], 'pdf')
        self.assertEqual(response.json['extracted_text'], 'Exam notice')
        self.assertEqual(response.json['summary'], SUMMARY)
        self.assertEqual(response.json['summary_mode'], 'ai')
        self.assertNotIn('warning', response.json)
        gemini_class.assert_called_once_with(
            'test-key', 'test-model', timeout_ms=15_000, retry_attempts=2,
        )

    @patch('routes.summarize.extract_document_text')
    @patch('routes.summarize.GeminiService')
    def test_jpg_jpeg_and_png_are_accepted(self, gemini_class, extract_text):
        gemini_class.return_value.summarize_notice.return_value = SUMMARY
        extract_text.return_value = ('Notice', 'OCR text.', [])
        for filename, data in [('notice.jpg', image_bytes('jpeg')), ('notice.jpeg', image_bytes('jpeg')), ('notice.png', image_bytes('png'))]:
            with self.subTest(filename=filename):
                self.assertEqual(self.post_file(data, filename).status_code, 200)

    def test_unsupported_file_is_rejected(self):
        response = self.post_file(b'plain text', 'notice.txt')
        self.assertEqual(response.status_code, 415)

    def test_file_signature_must_match_extension(self):
        response = self.post_file(image_bytes('png'), 'notice.pdf')
        self.assertEqual(response.status_code, 415)

    def test_missing_file_is_rejected(self):
        response = self.client.post('/api/v1/summarize', data={})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json['success'])

    def test_empty_file_is_rejected(self):
        response = self.post_file(b'', 'notice.pdf')
        self.assertEqual(response.status_code, 400)

    def test_file_over_limit_is_rejected(self):
        response = self.post_file(b'%PDF-' + b'x' * (10 * 1024 * 1024), 'large.pdf')
        self.assertEqual(response.status_code, 413)

    def test_missing_gemini_key_returns_503(self):
        self.app.config['GEMINI_API_KEY'] = ''
        response = self.post_file(text_pdf_bytes(), 'exam_notice.pdf')
        self.assertEqual(response.status_code, 503)

    @patch('routes.summarize.extract_document_text')
    @patch('routes.summarize.GeminiService')
    def test_gemini_quota_error_uses_local_fallback(self, gemini_class, extract_text):
        extract_text.return_value = (NOTICE_TEXT, 'Direct PDF text.', [])
        gemini_class.return_value.summarize_notice.side_effect = GeminiRateLimitError('Quota exhausted')

        response = self.post_file(text_pdf_bytes(), 'seminar.pdf')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['summary_mode'], 'local')
        self.assertIn('temporarily unavailable', response.json['warning'])
        self.assertIn('15 December 2026', response.json['summary']['important_dates'])
        self.assertTrue(any(
            'register by 15 december 2026' in item.lower()
            for item in response.json['summary']['action_items']
        ))

    @patch('routes.summarize.extract_document_text')
    @patch('routes.summarize.GeminiService')
    def test_gemini_503_uses_local_fallback(self, gemini_class, extract_text):
        extract_text.return_value = (NOTICE_TEXT, 'Direct PDF text.', [])
        gemini_class.return_value.summarize_notice.side_effect = GeminiServiceUnavailableError('High demand')

        response = self.post_file(text_pdf_bytes(), 'seminar.pdf')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['summary_mode'], 'local')

    @patch('routes.summarize.extract_document_text')
    @patch('routes.summarize.GeminiService')
    def test_gemini_timeout_uses_local_fallback(self, gemini_class, extract_text):
        extract_text.return_value = (NOTICE_TEXT, 'Direct PDF text.', [])
        gemini_class.return_value.summarize_notice.side_effect = GeminiRequestTimeoutError('Timed out')

        response = self.post_file(text_pdf_bytes(), 'seminar.pdf')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['summary_mode'], 'local')

    @patch('routes.summarize.extract_document_text')
    @patch('routes.summarize.GeminiService')
    def test_empty_extracted_text_remains_an_error(self, _gemini_class, extract_text):
        extract_text.return_value = ('', 'Direct PDF text.', [])
        response = self.post_file(text_pdf_bytes(), 'empty.pdf')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json['success'])

    @patch('routes.summarize.GeminiService')
    def test_gemini_failure_returns_503(self, gemini_class):
        gemini_class.side_effect = GeminiServiceUnavailableError('Gemini is unavailable.')
        response = self.post_file(text_pdf_bytes(), 'exam_notice.pdf')
        self.assertEqual(response.status_code, 503)


class DocumentExtractionTests(unittest.TestCase):
    def make_pdf(self, with_text: bool) -> str:
        document = fitz.open()
        page = document.new_page()
        if with_text:
            page.insert_text((72, 72), 'Page one notice text.')
        temporary_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temporary_file.write(document.tobytes())
        temporary_file.close()
        document.close()
        return temporary_file.name

    def test_text_pdf_preserves_page_text(self):
        path = self.make_pdf(with_text=True)
        try:
            text, source, warnings = extract_document_text(Path(path), 'pdf', 'application/pdf', None)
            self.assertIn('Page one notice text.', text)
            self.assertIn('directly', source)
            self.assertEqual(warnings, [])
        finally:
            os.unlink(path)

    def test_scanned_pdf_uses_vision_ocr(self):
        class FakeGemini:
            def extract_text_from_image(self, *_args):
                return 'OCR transcribed notice text.'

        path = self.make_pdf(with_text=False)
        try:
            text, source, warnings = extract_document_text(Path(path), 'pdf', 'application/pdf', FakeGemini())
            self.assertIn('OCR transcribed notice text.', text)
            self.assertIn('vision OCR', source)
            self.assertTrue(warnings)
        finally:
            os.unlink(path)


class GeminiServiceTests(unittest.TestCase):
    @patch('services.gemini_service.genai.Client')
    def test_gemini_failures_are_logged_without_api_key(self, client_class):
        service = GeminiService('test-secret-key', 'test-model')
        self.assertEqual(client_class.call_args.kwargs['http_options'].timeout, 15_000)
        retry_options = client_class.call_args.kwargs['http_options'].retry_options
        self.assertEqual(retry_options.attempts, 2)
        self.assertEqual(retry_options.http_status_codes, [429, 500, 502, 503, 504])
        service.client.models.generate_content.side_effect = RuntimeError('Connection failed for test-secret-key')

        with self.assertLogs('services.gemini_service', level='ERROR') as logs:
            with self.assertRaises(GeminiServiceUnavailableError):
                service.extract_text_from_image(b'image', 'image/png', 'notice.png')

        output = '\n'.join(logs.output)
        self.assertIn('exception_type=RuntimeError', output)
        self.assertIn('[REDACTED]', output)
        self.assertNotIn('test-secret-key', output)

    @patch('services.gemini_service.genai.Client')
    def test_gemini_timeout_has_bounded_safe_error(self, _client_class):
        service = GeminiService('test-key', 'test-model')
        service.client.models.generate_content.side_effect = httpx.ReadTimeout('request timed out')

        with self.assertRaises(GeminiRequestTimeoutError) as raised:
            service.summarize_notice('notice text', 'direct extraction', [])

        self.assertEqual(raised.exception.status_code, 504)
        self.assertEqual(str(raised.exception), 'Gemini summarisation timed out. Please try again.')

    def test_provider_errors_map_to_distinct_safe_statuses(self):
        class ProviderError(Exception):
            def __init__(self, code):
                self.code = code

        self.assertIsInstance(
            GeminiService._request_error(ProviderError(429), 'summarisation'), GeminiRateLimitError,
        )
        self.assertIsInstance(
            GeminiService._request_error(ProviderError(401), 'summarisation'), GeminiAuthenticationError,
        )
        self.assertIsInstance(
            GeminiService._request_error(ProviderError(404), 'summarisation'), GeminiModelNotFoundError,
        )


class LocalSummarizerTests(unittest.TestCase):
    def test_local_fallback_extracts_summary_and_notice_details(self):
        summary = summarize_locally(NOTICE_TEXT, 'Direct PDF text.', [])

        self.assertIn('seminar', summary['short_summary'].lower())
        self.assertLess(len(summary['detailed_summary']), len(NOTICE_TEXT))
        self.assertEqual(summary['notice_title'], 'COLLEGE NOTICE: Annual Science Seminar')
        self.assertIn('15 December 2026', summary['important_dates'])
        self.assertIn('20 December 2026', summary['event_dates'])
        self.assertIn('final-year B.Sc. students', summary['target_audience'])
        self.assertIn('Main Auditorium', summary['venue'])
        self.assertIn('college ID card copy', summary['required_documents'][0])
        self.assertIn('science@example.edu', summary['contact_information'])

    def test_local_fallback_uses_not_mentioned_without_inventing_fields(self):
        summary = summarize_locally('NOTICE\nThe library will remain open on weekdays.', 'Direct PDF text.', [])

        self.assertEqual(summary['event_dates'], [NOT_MENTIONED])
        self.assertEqual(summary['venue'], NOT_MENTIONED)
        self.assertEqual(summary['contact_information'], NOT_MENTIONED)

if __name__ == '__main__':
    unittest.main()
