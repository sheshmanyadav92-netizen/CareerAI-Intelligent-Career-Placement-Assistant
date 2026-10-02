import logging
import re
from importlib.resources import files
from time import perf_counter

from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings
from app.core.errors import (
    AIConfigurationError,
    AIInvalidOutputError,
    AIProviderError,
    AIProviderTimeoutError,
    ValidationError,
)
from app.schemas.job_analysis import JobAnalysisOutput
from app.services.llm.base import (
    LLMConfigurationFailure,
    LLMProvider,
    LLMProviderError,
    LLMTimeoutFailure,
)
from app.services.resume_analysis import parse_json_object

logger = logging.getLogger(__name__)

_CORRECTION = (
    "Your previous response did not match the required schema or evidence rules. "
    "Return one corrected JSON object only. Do not explain the correction."
)
_WHITESPACE = re.compile(r"\s+")


def _normalize_whitespace(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def _validate_evidence(analysis: JobAnalysisOutput, job_text: str) -> None:
    normalized_job_text = _normalize_whitespace(job_text)
    for field_name in JobAnalysisOutput.model_fields:
        for item in getattr(analysis, field_name):
            quote = _normalize_whitespace(item.evidence_quote)
            if quote not in normalized_job_text:
                raise ValueError("Evidence must be quoted from the job description.")


def _read_prompt(filename: str) -> str:
    return files("app.prompts").joinpath(filename).read_text(encoding="utf-8")


class JobAnalysisExtractionService:
    def __init__(self, provider: LLMProvider, settings: Settings) -> None:
        self._provider = provider
        self._settings = settings
        self._system_prompt = _read_prompt("job_analysis_v1_system.txt")
        self._user_prompt = _read_prompt("job_analysis_v1_user.txt")

    async def analyze(self, job_text: str) -> JobAnalysisOutput:
        if not job_text.strip():
            raise ValidationError(
                code="EMPTY_JOB_DESCRIPTION",
                status_code=422,
                message="Enter job-description text before analysis.",
            )
        if len(job_text) > self._settings.llm_max_input_chars:
            raise ValidationError(
                code="JOB_DESCRIPTION_TOO_LONG",
                status_code=422,
                message="The job description exceeds the analysis text limit.",
            )

        started_at = perf_counter()
        correction = ""
        for attempt in range(2):
            prompt = self._user_prompt.format(
                job_description=job_text,
                correction=correction,
            )
            try:
                raw_output = await self._provider.generate(
                    prompt,
                    system_prompt=self._system_prompt,
                    timeout=self._settings.llm_timeout_seconds,
                )
            except LLMTimeoutFailure:
                logger.warning(
                    "job_analysis_failed category=timeout duration_ms=%.2f",
                    (perf_counter() - started_at) * 1000,
                )
                raise AIProviderTimeoutError from None
            except LLMConfigurationFailure:
                logger.warning("job_analysis_failed category=configuration")
                raise AIConfigurationError from None
            except LLMProviderError as error:
                logger.warning(
                    "job_analysis_failed category=provider exception_type=%s",
                    type(error).__name__,
                )
                raise AIProviderError from None

            try:
                parsed = parse_json_object(raw_output)
                analysis = JobAnalysisOutput.model_validate(parsed)
                _validate_evidence(analysis, job_text)
            except (PydanticValidationError, ValueError):
                if attempt < self._settings.llm_max_retries:
                    correction = _CORRECTION
                    continue
                logger.warning("job_analysis_failed category=invalid_output")
                raise AIInvalidOutputError from None

            logger.info(
                "job_analysis_succeeded duration_ms=%.2f",
                (perf_counter() - started_at) * 1000,
            )
            return analysis

        raise AIInvalidOutputError
