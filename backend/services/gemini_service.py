"""Gemini OCR and structured notice summarisation service."""

import json
import logging
from typing import Any

import httpx
from google import genai
from google.genai import types


logger = logging.getLogger(__name__)


class GeminiServiceError(RuntimeError):
    """Base error for safe, client-facing Gemini failures."""

    status_code = 503


class GeminiServiceUnavailableError(GeminiServiceError):
    """Raised when Gemini cannot provide a safe usable response."""


class GeminiRequestTimeoutError(GeminiServiceError):
    status_code = 504


class GeminiRateLimitError(GeminiServiceError):
    status_code = 429


class GeminiAuthenticationError(GeminiServiceError):
    status_code = 502


class GeminiModelNotFoundError(GeminiServiceError):
    status_code = 502


class GeminiInvalidResponseError(GeminiServiceError):
    status_code = 502


class GeminiConfigurationError(GeminiServiceError):
    """Raised when Gemini has not been configured locally."""


SUMMARY_SCHEMA: dict[str, Any] = {
    'type': 'OBJECT',
    'properties': {
        'notice_title': {'type': 'STRING'},
        'short_summary': {'type': 'STRING'},
        'detailed_summary': {'type': 'STRING'},
        'important_dates': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'event_dates': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'target_audience': {'type': 'STRING'},
        'department': {'type': 'STRING'},
        'venue': {'type': 'STRING'},
        'required_documents': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'contact_information': {'type': 'STRING'},
        'urgency': {'type': 'STRING', 'enum': ['High', 'Medium', 'Low']},
        'action_items': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'important_instructions': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'source_information': {'type': 'STRING'},
        'uncertainty_warnings': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
    },
    'required': [
        'notice_title', 'short_summary', 'detailed_summary', 'important_dates',
        'event_dates', 'target_audience', 'department', 'venue',
        'required_documents', 'contact_information', 'urgency', 'action_items',
        'important_instructions', 'source_information', 'uncertainty_warnings',
    ],
}


class GeminiService:
    """Uses the official Google GenAI SDK while keeping credentials server-side."""

    def __init__(self, api_key: str | None, model: str, *, timeout_ms: int = 15_000, retry_attempts: int = 2) -> None:
        if not api_key:
            raise GeminiConfigurationError('Gemini is not configured on the server.')
        self._api_key = api_key.strip()
        self.client = genai.Client(
            api_key=self._api_key,
            http_options=types.HttpOptions(
                timeout=timeout_ms,
                retry_options=types.HttpRetryOptions(
                    attempts=retry_attempts,
                    initial_delay=1,
                    max_delay=2,
                    http_status_codes=[429, 500, 502, 503, 504],
                ),
            ),
        )
        self.model = model

    def extract_text_from_image(self, image_data: bytes, mime_type: str, source_label: str) -> str:
        prompt = (
            'Transcribe all readable text in this college notice image exactly as shown. '
            'Preserve wording, dates, names, numbers, and line order where possible. '
            'Do not infer missing content. Mark unclear areas as [unclear] or [unreadable]. '
            f'Source: {source_label}.'
        )
        try:
            logger.info('Gemini OCR request started: model=%s', self.model)
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt, types.Part.from_bytes(data=image_data, mime_type=mime_type)],
            )
            text = (response.text or '').strip()
        except Exception as error:  # SDK exceptions vary by transport and version.
            self._log_request_error('OCR', error)
            raise self._request_error(error, 'OCR') from error
        logger.info('Gemini OCR request completed: model=%s', self.model)
        if not text:
            raise GeminiInvalidResponseError('Gemini OCR returned no readable text.')
        return text

    def summarize_notice(self, extracted_text: str, source_information: str, warnings: list[str]) -> dict[str, Any]:
        prompt = f'''Summarise this college notice using only the supplied text.
Return JSON matching the requested schema. Never invent dates, deadlines, names, instructions, or urgency.
Use "Not specified in the notice" when a scalar field is absent, and [] when an array field has no supported entries.
Urgency must be High, Medium, or Low; use Low when no urgency evidence is stated.
Include source_information exactly as provided. Include all provided uncertainty warnings and add warnings only for genuine ambiguities.

SOURCE INFORMATION: {source_information}
KNOWN WARNINGS: {json.dumps(warnings)}
NOTICE TEXT:
{extracted_text}'''
        try:
            logger.info('Gemini summarisation request started: model=%s', self.model)
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=SUMMARY_SCHEMA,
                ),
            )
            payload = json.loads((response.text or '').strip())
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            self._log_request_error('summarisation response parsing', error)
            raise GeminiInvalidResponseError('Gemini returned an invalid summary response.') from error
        except Exception as error:
            self._log_request_error('summarisation', error)
            raise self._request_error(error, 'summarisation') from error
        logger.info('Gemini summarisation request completed: model=%s', self.model)
        return _normalise_summary(payload, source_information, warnings)

    @staticmethod
    def _request_error(error: Exception, operation: str) -> GeminiServiceError:
        if isinstance(error, httpx.TimeoutException):
            return GeminiRequestTimeoutError(f'Gemini {operation} timed out. Please try again.')

        status_code = getattr(error, 'code', None)
        if status_code == 429:
            return GeminiRateLimitError('Gemini rate limit reached. Please try again shortly.')
        if status_code in {401, 403}:
            return GeminiAuthenticationError('Gemini authentication was rejected by the provider.')
        if status_code == 404:
            return GeminiModelNotFoundError('The configured Gemini model is unavailable for this API key.')
        if status_code == 503:
            return GeminiServiceUnavailableError('Gemini is temporarily unavailable. Please try again shortly.')
        return GeminiServiceUnavailableError(f'Gemini {operation} is currently unavailable.')

    def _log_request_error(self, operation: str, error: Exception) -> None:
        """Log actionable Gemini failures without leaking credentials or uploads."""
        message = str(getattr(error, 'message', error)).replace(self._api_key, '[REDACTED]')
        logger.error(
            'Gemini %s failed: exception_type=%s http_status=%s api_status=%s message=%s',
            operation,
            type(error).__name__,
            getattr(error, 'code', None),
            getattr(error, 'status', None),
            message,
        )


def _normalise_summary(payload: Any, source_information: str, warnings: list[str]) -> dict[str, Any]:
    """Defensively normalise model output before it reaches the API response."""
    if not isinstance(payload, dict):
        raise GeminiInvalidResponseError('Gemini returned an invalid summary response.')

    def text(name: str) -> str:
        value = payload.get(name)
        return value.strip() if isinstance(value, str) and value.strip() else 'Not specified in the notice'

    def text_list(name: str) -> list[str]:
        value = payload.get(name)
        return [item.strip() for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []

    urgency = payload.get('urgency')
    return {
        'notice_title': text('notice_title'),
        'short_summary': text('short_summary'),
        'detailed_summary': text('detailed_summary'),
        'important_dates': text_list('important_dates'),
        'event_dates': text_list('event_dates'),
        'target_audience': text('target_audience'),
        'department': text('department'),
        'venue': text('venue'),
        'required_documents': text_list('required_documents'),
        'contact_information': text('contact_information'),
        'urgency': urgency if urgency in {'High', 'Medium', 'Low'} else 'Low',
        'action_items': text_list('action_items'),
        'important_instructions': text_list('important_instructions'),
        'source_information': source_information,
        'uncertainty_warnings': list(dict.fromkeys(warnings + text_list('uncertainty_warnings'))),
    }
