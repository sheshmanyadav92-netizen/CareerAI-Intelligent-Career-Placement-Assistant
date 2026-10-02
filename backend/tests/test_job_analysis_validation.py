import asyncio
import json
from collections.abc import Sequence
from typing import Any

import pytest

from app.core.config import Settings
from app.core.errors import AIInvalidOutputError, ValidationError
from app.schemas.job_analysis import JobAnalysisOutput
from app.services.llm.base import LLMProvider
from app.services.job_analysis import JobAnalysisExtractionService


def valid_output() -> dict[str, Any]:
    return {
        "required_skills": [
            {
                "original_text": "Python",
                "evidence_quote": "Strong Python skills",
            }
        ],
        "preferred_skills": [],
        "unspecified_skills": [],
        "programming_languages": [],
        "frameworks": [],
        "tools": [],
        "experience_requirements": [],
        "education_requirements": [],
        "role_responsibilities": [],
    }


class FakeProvider:
    def __init__(self, responses: Sequence[str]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []
        self.system_prompts: list[str | None] = []
        self.timeouts: list[float | None] = []

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        timeout: float | None = None,
    ) -> str:
        self.prompts.append(prompt)
        self.system_prompts.append(system_prompt)
        self.timeouts.append(timeout)
        return self.responses.pop(0)


def run_analysis(
    provider: LLMProvider,
    *,
    job_text: str = "Strong\n  Python skills",
    settings: Settings | None = None,
) -> JobAnalysisOutput:
    service = JobAnalysisExtractionService(provider, settings or Settings(_env_file=None))
    return asyncio.run(service.analyze(job_text))


def test_valid_output_checks_evidence_with_normalized_whitespace() -> None:
    provider = FakeProvider([json.dumps(valid_output())])

    result = run_analysis(provider)

    assert result.required_skills[0].original_text == "Python"
    assert len(provider.prompts) == 1
    assert "untrusted data" in (provider.system_prompts[0] or "")
    assert provider.timeouts == [30.0]


def test_unsupported_evidence_retries_then_fails_safely() -> None:
    output = valid_output()
    output["required_skills"][0]["evidence_quote"] = "Invented qualification"
    provider = FakeProvider([json.dumps(output), json.dumps(output)])

    with pytest.raises(AIInvalidOutputError):
        run_analysis(provider)

    assert len(provider.prompts) == 2
    assert "corrected JSON" in provider.prompts[1]
    assert "Invented qualification" not in str(AIInvalidOutputError())


def test_missing_required_output_group_retries_then_fails() -> None:
    output = valid_output()
    del output["tools"]
    provider = FakeProvider([json.dumps(output), json.dumps(output)])

    with pytest.raises(AIInvalidOutputError):
        run_analysis(provider)

    assert len(provider.prompts) == 2


def test_empty_and_oversized_text_are_rejected_before_provider_call() -> None:
    provider = FakeProvider([])
    config = Settings(_env_file=None, llm_max_input_chars=8)

    with pytest.raises(ValidationError) as empty_error:
        run_analysis(provider, job_text=" ")
    assert empty_error.value.code == "EMPTY_JOB_DESCRIPTION"

    with pytest.raises(ValidationError) as size_error:
        run_analysis(provider, job_text="x" * 9, settings=config)
    assert size_error.value.code == "JOB_DESCRIPTION_TOO_LONG"
    assert provider.prompts == []
