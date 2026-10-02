from copy import deepcopy

import httpx
from app.core.config import Settings
from app.schemas.resume_analysis import ResumeAnalysisResult
from app.services.llm.base import (
    LLMConfigurationFailure,
    LLMProviderError,
    LLMTimeoutFailure,
)

_CHAT_URL = "http://127.0.0.1:11434/api/chat"
_GENERATE_URL = "http://127.0.0.1:11434/api/generate"
_MODEL_KEEP_ALIVE = "24h"


def _response_schema() -> dict[str, object]:
    schema = deepcopy(ResumeAnalysisResult.model_json_schema())
    schema["properties"].pop("ai_observations")
    schema["required"] = ["extracted_facts"]
    schema["$defs"].pop("ResumeAIAnalysis")
    schema["$defs"].pop("ResumeObservation")
    schema["$defs"]["ExtractedResumeFacts"]["required"] = list(
        schema["$defs"]["ExtractedResumeFacts"]["properties"]
    )
    return schema


class OllamaProvider:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if settings.llm_provider != "ollama" or not settings.llm_model.strip():
            raise LLMConfigurationFailure

        self._model = settings.llm_model
        self._timeout = settings.llm_timeout_seconds
        self._transport = transport

    async def warmup(self) -> None:
        try:
            async with httpx.AsyncClient(
                timeout=max(120.0, self._timeout),
                transport=self._transport,
            ) as client:
                response = await client.post(
                    _GENERATE_URL,
                    json={
                        "model": self._model,
                        "prompt": " ",
                        "stream": False,
                        "keep_alive": _MODEL_KEEP_ALIVE,
                        "options": {"num_predict": 1},
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException:
            raise LLMTimeoutFailure from None
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403, 404}:
                raise LLMConfigurationFailure from None
            raise LLMProviderError from None
        except httpx.RequestError:
            raise LLMProviderError from None

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        timeout: float | None = None,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(
                timeout=timeout or self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    _CHAT_URL,
                    json={
                        "model": self._model,
                        "messages": messages,
                        "stream": False,
                        "keep_alive": _MODEL_KEEP_ALIVE,
                        "format": _response_schema(),
                        "options": {
                            "temperature": 0,
                            "num_ctx": 8192,
                            "num_predict": 768,
                        },
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException:
            raise LLMTimeoutFailure from None
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403, 404}:
                raise LLMConfigurationFailure from None
            raise LLMProviderError from None
        except httpx.RequestError:
            raise LLMProviderError from None

        try:
            content = response.json()["message"]["content"]
        except (KeyError, TypeError, ValueError):
            raise LLMProviderError from None

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError
        return content
