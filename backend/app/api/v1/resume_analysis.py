import logging
from typing import Annotated

from app.core.config import Settings
from app.core.errors import AuthorizationError, ValidationError
from app.schemas.resume_upload import ResumeUploadAnalysisResponse
from app.services.llm.base import LLMProvider
from app.services.llm.provider import create_llm_provider
from app.services.resume_analysis import ResumeAnalysisService
from app.services.resume_validation import validate_resume_upload
from fastapi import APIRouter, Depends, File, Request, UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resume-analysis", tags=["resume-analysis"])


def get_settings() -> Settings:
    return Settings()


def get_resume_analysis_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ResumeAnalysisService:
    provider: LLMProvider = create_llm_provider(settings)
    return ResumeAnalysisService(provider, settings)


@router.post("/analyze", response_model=ResumeUploadAnalysisResponse)
async def analyze_resume_upload(
    request: Request,
    file: Annotated[UploadFile, File()],
    settings: Annotated[Settings, Depends(get_settings)],
    analysis_service: Annotated[
        ResumeAnalysisService,
        Depends(get_resume_analysis_service),
    ],
) -> ResumeUploadAnalysisResponse:
    if settings.is_production:
        raise AuthorizationError()

    validated = await validate_resume_upload(file, settings)

    try:
        await file.seek(0)
        reader = PdfReader(file.file, strict=True)
        resume_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except (OSError, PdfReadError, ValueError):
        raise ValidationError(
            code="INVALID_FILE",
            status_code=400,
            message="The PDF text could not be extracted.",
            details=[{"field": "file", "message": "The PDF text could not be extracted."}],
        ) from None

    if not resume_text.strip():
        raise ValidationError(
            code="INVALID_RESUME_TEXT",
            status_code=422,
            message="No selectable text was found in this PDF. Scanned resumes need OCR.",
            details=[{"field": "file", "message": "No selectable text was found in this PDF."}],
        )

    warmup_task = getattr(request.app.state, "local_model_warmup_task", None)
    if warmup_task is not None:
        await warmup_task

    result = await analysis_service.analyze(resume_text)
    logger.info(
        "resume_upload_analysis_completed page_count=%d size_bytes=%d",
        validated.page_count,
        validated.size_bytes,
    )
    return ResumeUploadAnalysisResponse(
        filename=validated.filename,
        page_count=validated.page_count,
        size_bytes=validated.size_bytes,
        result=result,
    )
