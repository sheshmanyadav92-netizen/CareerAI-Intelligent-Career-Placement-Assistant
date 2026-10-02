import json
import logging
import re
from importlib.resources import files
from time import perf_counter
from typing import Any

from app.core.config import Settings
from app.core.errors import (
    AIConfigurationError,
    AIInvalidOutputError,
    AIProviderError,
    AIProviderTimeoutError,
    NotFoundError,
    ValidationError,
)
from app.schemas.resume_analysis import (
    ExtractedResumeFacts,
    ResumeAIAnalysis,
    ResumeAnalysisResult,
    ResumeObservation,
)
from app.services.llm.base import (
    LLMConfigurationFailure,
    LLMProvider,
    LLMProviderError,
    LLMTimeoutFailure,
)
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)

_CORRECTION = (
    "Correct the previous response to match the required extracted_facts JSON "
    "shape. Every fact must be copied from the resume. Remove unsupported facts."
)
_OBSERVATION_FIELDS = (
    "strengths",
    "improvement_areas",
    "skills_observations",
    "experience_observations",
    "education_observations",
    "recommended_next_steps",
)
_WHITESPACE = re.compile(r"\s+")


def _normalize_whitespace(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def _source_quote(candidate: str, resume_text: str) -> str | None:
    normalized_candidate = _normalize_whitespace(candidate)
    normalized_resume = _normalize_whitespace(resume_text)
    match = re.search(re.escape(normalized_candidate), normalized_resume, re.IGNORECASE)
    return normalized_resume[match.start() : match.end()] if match else None


def _canonicalize_facts(
    facts: ExtractedResumeFacts,
    resume_text: str,
) -> tuple[ExtractedResumeFacts, int]:
    values: dict[str, list[str]] = {}
    discarded_count = 0
    for field_name in ExtractedResumeFacts.model_fields:
        values[field_name] = []
        for candidate in getattr(facts, field_name):
            quote = _source_quote(candidate, resume_text)
            if quote is None:
                discarded_count += 1
            elif quote not in values[field_name]:
                values[field_name].append(quote)
    return ExtractedResumeFacts.model_validate(values), discarded_count


def _analysis_from_facts(facts: ExtractedResumeFacts) -> ResumeAIAnalysis:
    summary = next(
        (
            fact
            for field_name in (
                "experience",
                "projects",
                "education",
                "skills",
                "certifications",
            )
            for fact in getattr(facts, field_name)
        ),
        None,
    )
    return ResumeAIAnalysis(
        summary=summary,
        summary_evidence=[summary] if summary else [],
    )


def parse_json_object(raw_output: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for offset, character in enumerate(raw_output):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(raw_output[offset:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("No JSON object found.")


def _validate_evidence(
    analysis: ResumeAIAnalysis,
    extracted_facts: ExtractedResumeFacts,
    resume_text: str,
) -> None:
    normalized_resume = _normalize_whitespace(resume_text)
    evidence = list(analysis.summary_evidence)
    for field_name in _OBSERVATION_FIELDS:
        observations: list[ResumeObservation] = getattr(analysis, field_name)
        evidence.extend(quote for item in observations for quote in item.evidence)
    if any(_normalize_whitespace(quote) not in normalized_resume for quote in evidence):
        raise ValueError("Evidence must be quoted from the supplied resume.")
    claims = [analysis.summary] if analysis.summary else []
    for field_name in _OBSERVATION_FIELDS:
        observations = getattr(analysis, field_name)
        claims.extend(item.observation for item in observations)
    if any(_normalize_whitespace(claim) not in normalized_resume for claim in claims):
        raise ValueError("Analysis claims must be quoted from the supplied resume.")
    for field_name in ExtractedResumeFacts.model_fields:
        facts: list[str] = getattr(extracted_facts, field_name)
        if any(_normalize_whitespace(fact) not in normalized_resume for fact in facts):
            raise ValueError("Extracted facts must be quoted from the supplied resume.")


def _read_prompt(filename: str) -> str:
    return files("app.prompts").joinpath(filename).read_text(encoding="utf-8")


class ResumeAnalysisService:
    def __init__(self, provider: LLMProvider, settings: Settings) -> None:
        self._provider = provider
        self._settings = settings
        self._system_prompt = _read_prompt("resume_analysis_system.txt")
        self._user_prompt = _read_prompt("resume_analysis_user.txt")

    @staticmethod
    def _lookup_resume_for_user(
        resume: Any | None,
        *,
        user_id: int | None,
        resume_id: int | None = None,
        resume_lookup: Any | None = None,
    ) -> Any | None:
        if resume is not None:
            return resume

        if resume_id is None or resume_lookup is None:
            return None

        try:
            return resume_lookup(resume_id)
        except TypeError:
            lookup_method = getattr(resume_lookup, "get_by_id", None)
            if lookup_method is None:
                return None
            return lookup_method(resume_id)

    def _persist_result(
        self,
        result: ResumeAnalysisResult,
        *,
        resume_id: int | None,
        analysis_store: Any | None,
    ) -> Any | None:
        if analysis_store is None or resume_id is None:
            return None

        payload = {
            "resume_id": resume_id,
            "extracted_facts": result.extracted_facts.model_dump(mode="json"),
            "ai_observations": result.ai_observations.model_dump(mode="json"),
        }

        save_method = getattr(analysis_store, "save", None)
        if save_method is not None:
            return save_method(**payload)

        update_method = getattr(analysis_store, "upsert", None)
        if update_method is not None:
            return update_method(**payload)

        create_method = getattr(analysis_store, "create", None)
        if create_method is not None:
            return create_method(**payload)

        if callable(analysis_store):
            return analysis_store(**payload)

        return None

    async def analyze(
        self,
        resume_text: str,
        *,
        extracted_facts: ExtractedResumeFacts | None = None,
    ) -> ResumeAnalysisResult:
        if not resume_text.strip():
            raise ValidationError(
                code="INVALID_RESUME_TEXT",
                status_code=422,
                message="The resume does not contain text to analyze.",
            )

        if len(resume_text) > self._settings.llm_max_input_chars:
            raise ValidationError(
                code="RESUME_TEXT_TOO_LONG",
                status_code=422,
                message="The resume exceeds the analysis text limit.",
            )

        bounded_text = resume_text

        started_at = perf_counter()
        correction = ""
        for attempt in range(self._settings.llm_max_retries + 1):
            prompt = self._user_prompt.format(
                resume_text=bounded_text,
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
                    "resume_analysis_failed category=timeout duration_ms=%.2f",
                    (perf_counter() - started_at) * 1000,
                )
                raise AIProviderTimeoutError from None
            except LLMConfigurationFailure:
                logger.warning("resume_analysis_failed category=configuration")
                raise AIConfigurationError from None
            except LLMProviderError as error:
                logger.warning(
                    "resume_analysis_failed category=provider exception_type=%s",
                    type(error).__name__,
                )
                raise AIProviderError from None

            try:
                parsed = parse_json_object(raw_output)
                parsed_facts = parsed.pop("extracted_facts", None)
                parsed_analysis = parsed.pop("ai_observations", None)
                validated_facts = (
                    ExtractedResumeFacts.model_validate(parsed_facts)
                    if parsed_facts is not None
                    else extracted_facts or ExtractedResumeFacts()
                )
                validated_facts, discarded_count = _canonicalize_facts(
                    validated_facts,
                    bounded_text,
                )
                if discarded_count:
                    logger.warning(
                        "resume_analysis_discarded_unsupported_facts count=%d",
                        discarded_count,
                    )
                analysis_payload = parsed_analysis if parsed_analysis is not None else parsed
                analysis = (
                    ResumeAIAnalysis.model_validate(analysis_payload)
                    if "summary" in analysis_payload
                    else _analysis_from_facts(validated_facts)
                )
                _validate_evidence(analysis, validated_facts, bounded_text)
                if "summary" not in analysis_payload and not analysis.summary:
                    raise ValueError("No supported facts were extracted.")
            except (PydanticValidationError, ValueError):
                if attempt < self._settings.llm_max_retries:
                    correction = _CORRECTION
                    continue
                logger.warning("resume_analysis_failed category=invalid_output")
                raise AIInvalidOutputError from None

            logger.info(
                "resume_analysis_succeeded duration_ms=%.2f",
                (perf_counter() - started_at) * 1000,
            )
            return ResumeAnalysisResult(
                extracted_facts=validated_facts,
                ai_observations=analysis,
            )

        raise AIInvalidOutputError

    async def analyze_resume(
        self,
        resume: Any | None = None,
        *,
        user_id: int | None = None,
        resume_id: int | None = None,
        resume_lookup: Any | None = None,
        analysis_store: Any | None = None,
        extracted_facts: ExtractedResumeFacts | None = None,
    ) -> ResumeAnalysisResult:
        resolved_resume = self._lookup_resume_for_user(
            resume,
            user_id=user_id,
            resume_id=resume_id,
            resume_lookup=resume_lookup,
        )
        if resolved_resume is None:
            raise NotFoundError()

        resume_user_id = getattr(resolved_resume, "user_id", None)
        if isinstance(resolved_resume, dict):
            resume_user_id = resolved_resume.get("user_id", resume_user_id)
        if user_id is not None and resume_user_id is not None and resume_user_id != user_id:
            raise NotFoundError()

        resume_text = getattr(resolved_resume, "extracted_text", None)
        if isinstance(resolved_resume, dict):
            resume_text = resolved_resume.get("extracted_text", resume_text)
        if resume_text is None:
            resume_text = ""

        result = await self.analyze(resume_text, extracted_facts=extracted_facts)

        stored_resume_id = getattr(resolved_resume, "id", None)
        if isinstance(resolved_resume, dict):
            stored_resume_id = resolved_resume.get("id", stored_resume_id)
        if stored_resume_id is None:
            stored_resume_id = resume_id
        self._persist_result(result, resume_id=stored_resume_id, analysis_store=analysis_store)
        return result

    async def analyze_stored_resume(
        self,
        resume: Any | None = None,
        *,
        user_id: int | None = None,
        resume_id: int | None = None,
        resume_lookup: Any | None = None,
        analysis_store: Any | None = None,
        extracted_facts: ExtractedResumeFacts | None = None,
    ) -> ResumeAnalysisResult:
        return await self.analyze_resume(
            resume,
            user_id=user_id,
            resume_id=resume_id,
            resume_lookup=resume_lookup,
            analysis_store=analysis_store,
            extracted_facts=extracted_facts,
        )

    async def analyze_by_resume_id(
        self,
        resume_id: int,
        *,
        user_id: int,
        resume_lookup: Any,
        analysis_store: Any | None = None,
        extracted_facts: ExtractedResumeFacts | None = None,
    ) -> ResumeAnalysisResult:
        return await self.analyze_resume(
            resume_id=resume_id,
            user_id=user_id,
            resume_lookup=resume_lookup,
            analysis_store=analysis_store,
            extracted_facts=extracted_facts,
        )