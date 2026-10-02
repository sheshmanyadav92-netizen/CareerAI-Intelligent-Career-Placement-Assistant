import asyncio
import sys
from io import BytesIO

import pytest
from fastapi import UploadFile
from pypdf import PdfWriter
from starlette.datastructures import Headers

from app.core.config import Settings
from app.core.errors import ValidationError
from app.services.resume_validation import ValidatedResume, validate_resume_upload


def make_pdf(page_count: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def make_upload(
    content: bytes,
    filename: str | None = "resume.pdf",
    content_type: str | None = "application/pdf",
) -> UploadFile:
    headers = Headers(
        {"content-type": content_type} if content_type is not None else {}
    )
    return UploadFile(file=BytesIO(content), filename=filename, headers=headers)


def validate(
    upload: UploadFile | None,
    settings: Settings | None = None,
) -> ValidatedResume:
    return asyncio.run(validate_resume_upload(upload, settings))


def test_valid_pdf_returns_safe_metadata() -> None:
    content = make_pdf()
    upload = make_upload(content)

    result = validate(upload, Settings(_env_file=None))

    assert result == ValidatedResume(
        filename="resume.pdf",
        content_type="application/pdf",
        size_bytes=len(content),
        page_count=1,
    )
    assert upload.file.tell() == 0


def test_missing_file_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        validate(None)

    assert error.value.code == "INVALID_FILE"
    assert error.value.status_code == 400


def test_missing_filename_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        validate(make_upload(make_pdf(), filename=None))

    assert error.value.code == "INVALID_FILE"


def test_unsupported_extension_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        validate(make_upload(make_pdf(), filename="resume.docx"))

    assert error.value.code == "UNSUPPORTED_FILE_TYPE"
    assert error.value.status_code == 415


def test_unsupported_content_type_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        validate(make_upload(make_pdf(), content_type="text/plain"))

    assert error.value.code == "UNSUPPORTED_FILE_TYPE"


def test_missing_content_type_is_allowed_when_signature_is_valid() -> None:
    assert validate(make_upload(make_pdf(), content_type=None)).content_type == "application/pdf"


def test_empty_file_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        validate(make_upload(b""))

    assert error.value.code == "EMPTY_FILE"


def test_non_pdf_renamed_with_pdf_extension_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        validate(make_upload(b"not a PDF", filename="resume.pdf"))

    assert error.value.code == "INVALID_FILE"


def test_corrupted_pdf_with_pdf_signature_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        validate(make_upload(b"%PDF- corrupted content"))

    assert error.value.code == "INVALID_FILE"
    assert error.value.message == "The file is not a valid PDF."


def test_oversized_file_is_rejected_while_reading() -> None:
    maximum_size = 1024 * 1024
    content = b"%PDF-" + b"x" * (maximum_size + 128 * 1024)
    upload = make_upload(content)
    settings = Settings(_env_file=None, max_upload_size_mb=1)

    with pytest.raises(ValidationError) as error:
        validate(upload, settings)

    assert error.value.code == "FILE_TOO_LARGE"
    assert error.value.status_code == 413
    assert upload.file.tell() < len(content)


def test_path_traversal_filename_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        validate(make_upload(make_pdf(), filename="..\\..\\resume.pdf"))

    assert error.value.code == "INVALID_FILE"


def test_password_protected_pdf_is_rejected_safely() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    output = BytesIO()
    writer.write(output)

    with pytest.raises(ValidationError) as error:
        validate(make_upload(output.getvalue()))

    assert error.value.code == "INVALID_FILE"
    assert "secret" not in str(error.value)


def test_page_limit_is_enforced() -> None:
    with pytest.raises(ValidationError) as error:
        validate(make_upload(make_pdf(page_count=51)))

    assert error.value.code == "INVALID_FILE"


def test_validation_errors_do_not_include_file_contents() -> None:
    private_content = b"private-resume-content"

    with pytest.raises(ValidationError) as error:
        validate(make_upload(private_content, filename="resume.docx"))

    assert private_content.decode() not in str(error.value)
    assert private_content.decode() not in error.value.message
    assert all(private_content.decode() not in detail["message"] for detail in error.value.details)


def test_validation_does_not_require_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "app.core.database", None)

    result = validate(make_upload(make_pdf()), Settings(_env_file=None))

    assert result.page_count == 1