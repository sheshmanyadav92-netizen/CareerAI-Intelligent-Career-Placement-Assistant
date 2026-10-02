import asyncio
import json
from collections.abc import Sequence
from typing import Any

import httpx
import pytest
from app.core.config import Settings
from app.core.errors import (
    AIConfigurationError,
    AIInvalidOutputError,
    AIProviderError,
    AIProviderTimeoutError,
)
from app.schemas.resume_analysis import ExtractedResumeFacts
from app.services.llm.base import (
    LLMConfigurationFailure,
    LLMProviderError,
    LLMTimeoutFailure,
)
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.openai_provider import OpenAIChatCompletionsProvider
from app.services.llm.provider import create_llm_provider
from app.services.resume_analysis import ResumeAnalysisService
from pydantic import SecretStr


def valid_output() -> dict[str, Any]:
    return {
        "summary": "Built a Python web application.",
        "summary_evidence": ["Built a Python web application."],
        "strengths": [],
        "improvement_areas": [],
        "skills_observations": [],
        "experience_observations": [],
        "education_observations": [],
        "recommended_next_steps": [],
    }


class FakeProvider:
    def __init__(self, responses: Sequence[str | Exception]) -> None:
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
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, **overrides)


def analyze(
    provider: FakeProvider,
    *,
    resume_text: str = "Built a Python web application.",
    extracted_facts: ExtractedResumeFacts | None = None,
    config: Settings | None = None,
):
    service = ResumeAnalysisService(provider, config or settings())
    return asyncio.run(
        service.analyze(resume_text, extracted_facts=extracted_facts)
    )


def test_valid_response_returns_observations_and_separate_facts() -> None:
    provider = FakeProvider([json.dumps(valid_output())])
    facts = ExtractedResumeFacts(skills=["Python"])

    result = analyze(provider, extracted_facts=facts)

    assert result.extracted_facts.skills == ["Python"]
    assert result.ai_observations.summary == "Built a Python web application."
    assert len(provider.prompts) == 1
    assert provider.timeouts == [30.0]
    assert "Built a Python web application." in provider.prompts[0]


def test_valid_response_returns_ai_extracted_resume_facts() -> None:
    output = valid_output()
    output["extracted_facts"] = {
        "skills": ["Python"],
        "education": ["BSc Computer Science"],
        "experience": ["Built a Python web application."],
        "projects": [],
        "certifications": [],
    }
    provider = FakeProvider([json.dumps(output)])

    result = analyze(
        provider,
        resume_text="BSc Computer Science. Built a Python web application.",
    )

    assert result.extracted_facts.skills == ["Python"]
    assert result.extracted_facts.education == ["BSc Computer Science"]
    assert result.extracted_facts.experience == [
        "Built a Python web application."
    ]


def test_valid_nested_response_returns_facts_and_observations() -> None:
    output = {
        "extracted_facts": {
            "skills": ["Python"],
            "education": [],
            "experience": ["Built a Python web application."],
            "projects": [],
            "certifications": [],
        },
        "ai_observations": valid_output(),
    }
    provider = FakeProvider([json.dumps(output)])

    result = analyze(provider)

    assert result.extracted_facts.skills == ["Python"]
    assert result.ai_observations.summary == "Built a Python web application."


def test_unquoted_extracted_facts_are_discarded_without_losing_valid_analysis() -> None:
    output = valid_output()
    output["extracted_facts"] = {
        "skills": ["Invented skill"],
        "education": [],
        "experience": [],
        "projects": [],
        "certifications": [],
    }
    provider = FakeProvider([json.dumps(output)])

    result = analyze(provider)

    assert result.extracted_facts.skills == []
    assert result.ai_observations.summary == "Built a Python web application."
    assert len(provider.prompts) == 1


def test_invalid_json_retries_once_then_returns_valid_output() -> None:
    provider = FakeProvider(["not JSON", json.dumps(valid_output())])

    result = analyze(provider)

    assert result.ai_observations.summary is not None
    assert len(provider.prompts) == 2
    assert "Correct the previous response" in provider.prompts[1]


def test_invalid_schema_retries_then_fails_with_safe_error() -> None:
    invalid_schema = json.dumps({"summary": 42})
    provider = FakeProvider([invalid_schema, invalid_schema])

    with pytest.raises(AIInvalidOutputError) as error:
        analyze(provider)

    assert error.value.code == "AI_INVALID_OUTPUT"
    assert "42" not in str(error.value)
    assert len(provider.prompts) == 2


def test_invalid_json_twice_returns_controlled_error() -> None:
    provider = FakeProvider(["not JSON", "still not JSON"])

    with pytest.raises(AIInvalidOutputError) as error:
        analyze(provider)

    assert error.value.code == "AI_INVALID_OUTPUT"
    assert len(provider.prompts) == 2


def test_timeout_maps_to_safe_error_without_retry() -> None:
    provider = FakeProvider([LLMTimeoutFailure("private provider detail")])

    with pytest.raises(AIProviderTimeoutError) as error:
        analyze(provider)

    assert error.value.code == "AI_PROVIDER_TIMEOUT"
    assert "private provider detail" not in str(error.value)
    assert len(provider.prompts) == 1


def test_provider_error_maps_to_safe_error_without_retry() -> None:
    provider = FakeProvider([LLMProviderError("secret-key and raw response")])

    with pytest.raises(AIProviderError) as error:
        analyze(provider)

    assert error.value.code == "AI_PROVIDER_ERROR"
    assert "secret-key" not in str(error.value)
    assert "raw response" not in str(error.value)
    assert len(provider.prompts) == 1


def test_missing_resume_text_is_rejected_before_provider_call() -> None:
    provider = FakeProvider([])

    with pytest.raises(Exception) as error:
        analyze(provider, resume_text="  ")

    assert error.value.code == "INVALID_RESUME_TEXT"
    assert provider.prompts == []


def test_unquoted_evidence_retries_and_then_fails() -> None:
    unsupported = valid_output()
    unsupported["summary_evidence"] = ["A made-up quotation"]
    provider = FakeProvider([json.dumps(unsupported), json.dumps(unsupported)])

    with pytest.raises(AIInvalidOutputError):
        analyze(provider)

    assert len(provider.prompts) == 2


def test_unquoted_summary_and_observations_are_rejected() -> None:
    unsupported = valid_output()
    unsupported["summary"] = "The candidate has strong Python experience."
    unsupported["summary_evidence"] = ["Built a Python web application."]
    unsupported["strengths"] = [
        {
            "observation": "The candidate is an excellent engineer.",
            "evidence": ["Built a Python web application."],
        }
    ]
    provider = FakeProvider(
        [json.dumps(unsupported), json.dumps(unsupported)]
    )

    with pytest.raises(AIInvalidOutputError):
        analyze(provider)

    assert len(provider.prompts) == 2


def test_input_is_rejected_when_it_exceeds_the_limit() -> None:
    provider = FakeProvider([])
    resume_text = "Built a Python web application." + (" x" * 200)
    config = settings(llm_max_input_chars=64)

    with pytest.raises(Exception) as error:
        analyze(provider, resume_text=resume_text, config=config)

    assert error.value.code == "RESUME_TEXT_TOO_LONG"
    assert provider.prompts == []


def test_resume_analysis_accepts_exactly_50_observations() -> None:
    resume_text = " ".join(f"Skill {index}" for index in range(50))
    output = valid_output()
    output["summary"] = "Skill 0"
    output["summary_evidence"] = ["Skill 0"]
    output["skills_observations"] = [
        {"observation": f"Skill {index}", "evidence": [f"Skill {index}"]}
        for index in range(50)
    ]
    provider = FakeProvider([json.dumps(output)])

    result = analyze(provider, resume_text=resume_text)

    assert len(result.ai_observations.skills_observations) == 50


def test_resume_analysis_rejects_more_than_50_observations() -> None:
    resume_text = " ".join(f"Skill {index}" for index in range(51))
    output = valid_output()
    output["summary"] = "Skills overview."
    output["summary_evidence"] = ["Skill 0"]
    output["skills_observations"] = [
        {"observation": f"Skill {index}", "evidence": [f"Skill {index}"]}
        for index in range(51)
    ]
    provider = FakeProvider([json.dumps(output), json.dumps(output)])

    with pytest.raises(AIInvalidOutputError):
        analyze(provider, resume_text=resume_text)


def test_openai_adapter_uses_mock_transport_and_hides_api_key() -> None:
    seen_headers: dict[str, str] = {}

    def handle_request(request: httpx.Request) -> httpx.Response:
        seen_headers.update(dict(request.headers))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(valid_output())}}]
            },
        )

    config = settings(
        llm_provider="openai",
        llm_api_key=SecretStr("test-only-api-key"),
        llm_model="test-model",
    )
    provider = OpenAIChatCompletionsProvider(
        config,
        transport=httpx.MockTransport(handle_request),
    )

    result = asyncio.run(provider.generate("prompt", timeout=2))

    assert json.loads(result)["summary"] == valid_output()["summary"]
    assert seen_headers["authorization"] == "Bearer test-only-api-key"


def test_ollama_adapter_sends_json_chat_request_to_local_service() -> None:
    seen_requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(valid_output())}},
        )

    config = settings(llm_provider="ollama", llm_model="qwen2.5:3b")
    provider = OllamaProvider(config, transport=httpx.MockTransport(handle_request))

    result = asyncio.run(
        provider.generate(
            "resume prompt",
            system_prompt="system instructions",
            timeout=4,
        )
    )

    request = seen_requests[0]
    body = json.loads(request.content)
    assert request.url == "http://127.0.0.1:11434/api/chat"
    assert body["model"] == "qwen2.5:3b"
    assert body["stream"] is False
    assert body["keep_alive"] == "24h"
    assert body["options"] == {
        "temperature": 0,
        "num_ctx": 8192,
        "num_predict": 768,
    }
    assert body["format"]["required"] == ["extracted_facts"]
    assert set(body["format"]["properties"]) == {"extracted_facts"}
    assert "ResumeAIAnalysis" not in body["format"]["$defs"]
    assert set(body["format"]["$defs"]["ExtractedResumeFacts"]["required"]) == {
        "skills",
        "education",
        "experience",
        "projects",
        "certifications",
    }
    assert body["messages"][0] == {
        "role": "system",
        "content": "system instructions",
    }
    assert json.loads(result)["summary"] == valid_output()["summary"]


def test_ollama_warmup_loads_model_and_keeps_it_loaded() -> None:
    seen_requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(200, json={"response": "", "done": True})

    provider = OllamaProvider(
        settings(llm_provider="ollama", llm_model="qwen2.5:3b"),
        transport=httpx.MockTransport(handle_request),
    )

    asyncio.run(provider.warmup())

    request = seen_requests[0]
    body = json.loads(request.content)
    assert request.url == "http://127.0.0.1:11434/api/generate"
    assert body["model"] == "qwen2.5:3b"
    assert body["keep_alive"] == "24h"
    assert body["options"] == {"num_predict": 1}


def test_create_provider_selects_ollama_without_an_api_key() -> None:
    config = settings(llm_provider="ollama", llm_model="qwen2.5:3b")

    assert isinstance(create_llm_provider(config), OllamaProvider)


def test_ollama_adapter_maps_missing_model_to_configuration_failure() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(404))
    provider = OllamaProvider(
        settings(llm_provider="ollama", llm_model="missing-model"),
        transport=transport,
    )

    with pytest.raises(LLMConfigurationFailure):
        asyncio.run(provider.generate("prompt"))


def test_openai_adapter_maps_auth_failure_without_provider_details() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, text="private provider diagnostic")
    )
    config = settings(
        llm_provider="openai",
        llm_api_key=SecretStr("test-only-api-key"),
        llm_model="test-model",
    )
    provider = OpenAIChatCompletionsProvider(config, transport=transport)

    with pytest.raises(LLMConfigurationFailure) as error:
        asyncio.run(provider.generate("prompt"))

    assert "private provider diagnostic" not in str(error.value)
    assert "test-only-api-key" not in str(error.value)


def test_openai_adapter_requires_environment_configuration() -> None:
    with pytest.raises(LLMConfigurationFailure):
        OpenAIChatCompletionsProvider(settings())

    with pytest.raises(AIConfigurationError):
        from app.services.llm.provider import create_llm_provider

        create_llm_provider(settings())