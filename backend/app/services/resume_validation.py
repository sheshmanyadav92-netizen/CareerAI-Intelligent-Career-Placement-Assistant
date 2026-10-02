from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import Settings
from app.core.errors import ValidationError

_CHUNK_SIZE = 64 * 1024
_PDF_SIGNATURE = b"%PDF-"
_MAX_RESUME_PAGES = 50


@dataclass(frozen=True)
class ValidatedResume:
    filename: str
    content_type: str
    size_bytes: int
    page_count: int


def _validation_error(
    code: str,
    message: str,
    status_code: int,
) -> ValidationError:
    return ValidationError(
        code=code,
        status_code=status_code,
        message=message,
        details=[{"field": "file", "message": message}],
    )


async def validate_resume_upload(
    file: UploadFile | None,
    settings: Settings | None = None,
) -> ValidatedResume:
    """Validate a PDF upload without storing it or extracting its text.

    Malware scanning is not configured; successful validation does not establish
    that a PDF is malware-free.
    """
    if file is None:
        raise _validation_error("INVALID_FILE", "A file is required.", 400)

    filename = file.filename
    if not filename or not filename.strip():
        raise _validation_error("INVALID_FILE", "A filename is required.", 400)
    if (
        "\x00" in filename
        or "/" in filename
        or "\\" in filename
        or Path(filename).name != filename
    ):
        raise _validation_error("INVALID_FILE", "The filename is invalid.", 400)

    settings = settings or Settings()
    allowed_extensions = {
        extension.strip().lower() for extension in settings.allowed_resume_extensions
    }
    if Path(filename).suffix.lower() not in allowed_extensions:
        raise _validation_error(
            "UNSUPPORTED_FILE_TYPE",
            "Only PDF files are supported.",
            415,
        )

    content_type = (file.content_type or "").split(";", maxsplit=1)[0].strip().lower()
    allowed_content_types = {
        value.strip().lower() for value in settings.allowed_resume_content_types
    }
    if content_type and content_type not in allowed_content_types:
        raise _validation_error(
            "UNSUPPORTED_FILE_TYPE",
            "Only PDF files are supported.",
            415,
        )

    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    size_bytes = 0
    signature = bytearray()

    try:
        await file.seek(0)
        while chunk := await file.read(_CHUNK_SIZE):
            if len(signature) < len(_PDF_SIGNATURE):
                signature.extend(chunk[: len(_PDF_SIGNATURE) - len(signature)])

            size_bytes += len(chunk)
            if size_bytes > max_size_bytes:
                raise _validation_error(
                    "FILE_TOO_LARGE",
                    "The file exceeds the maximum upload size.",
                    413,
                )
    except (OSError, ValueError):
        raise _validation_error("INVALID_FILE", "The file could not be read.", 400) from None

    if size_bytes == 0:
        raise _validation_error("EMPTY_FILE", "The uploaded file is empty.", 422)
    if not bytes(signature).startswith(_PDF_SIGNATURE):
        raise _validation_error("INVALID_FILE", "The file is not a valid PDF.", 400)

    try:
        await file.seek(0)
        reader = PdfReader(file.file, strict=True)
        if reader.is_encrypted:
            raise _validation_error(
                "INVALID_FILE",
                "Password-protected PDFs are not supported.",
                400,
            )
        page_count = len(reader.pages)
        if page_count == 0:
            raise _validation_error("INVALID_FILE", "The PDF has no pages.", 400)
        if page_count > _MAX_RESUME_PAGES:
            raise _validation_error(
                "INVALID_FILE",
                "The PDF exceeds the maximum page count.",
                400,
            )
        await file.seek(0)
    except (OSError, PdfReadError, ValueError):
        raise _validation_error("INVALID_FILE", "The file is not a valid PDF.", 400) from None

    return ValidatedResume(
        filename=filename,
        content_type=content_type or "application/pdf",
        size_bytes=size_bytes,
        page_count=page_count,
    )