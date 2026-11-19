"""Server-side validation for supported notice uploads."""

from dataclasses import dataclass
from pathlib import Path


MAX_FILE_SIZE = 10 * 1024 * 1024
SUPPORTED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}


class UploadValidationError(ValueError):
    """Raised when an uploaded document cannot be processed."""


class UnsupportedFileTypeError(UploadValidationError):
    """Raised when a file is not one of the supported document formats."""


class FileTooLargeError(UploadValidationError):
    """Raised when a file exceeds the application upload limit."""


@dataclass(frozen=True)
class ValidatedFile:
    """Safe metadata inferred from an upload's extension and binary signature."""

    filename: str
    file_type: str
    mime_type: str


def validate_upload(filename: str, data: bytes) -> ValidatedFile:
    """Validate extension, size, and binary signature without trusting MIME headers."""
    if not filename:
        raise UploadValidationError('A file name is required.')
    if not data:
        raise UploadValidationError('The uploaded file is empty.')
    if len(data) > MAX_FILE_SIZE:
        raise FileTooLargeError('The uploaded file exceeds the 10 MB limit.')

    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError('Only PDF, JPG, JPEG, and PNG files are supported.')

    detected_type, mime_type = _detect_type(data)
    if not detected_type:
        raise UnsupportedFileTypeError('The file contents do not match a supported PDF or image format.')
    if extension == '.pdf' and detected_type != 'pdf':
        raise UnsupportedFileTypeError('The file extension does not match its contents.')
    if extension in {'.jpg', '.jpeg'} and detected_type != 'image':
        raise UnsupportedFileTypeError('The file extension does not match its contents.')
    if extension == '.png' and mime_type != 'image/png':
        raise UnsupportedFileTypeError('The file extension does not match its contents.')

    return ValidatedFile(filename=filename, file_type=detected_type, mime_type=mime_type)


def _detect_type(data: bytes) -> tuple[str | None, str | None]:
    if data.startswith(b'%PDF-'):
        return 'pdf', 'application/pdf'
    if data.startswith(b'\xff\xd8\xff'):
        return 'image', 'image/jpeg'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image', 'image/png'
    return None, None
