import httpx

from app.core.config import Settings
from app.services.llm.base import (
    LLMConfigurationFailure,
    LLMProviderError,
    LLMTimeoutFailure,
)

_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIChatCompletionsProvider:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if settings.llm_provider != "openai":
            raise LLMConfigurationFailure

        api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else ""
        if not api_key.strip() or not settings.llm_model.strip():
            raise LLMConfigurationFailure

        self._api_key = api_key
        self._model = settings.llm_model
        self._timeout = settings.llm_timeout_seconds
        self._transport = transport

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
                    _CHAT_COMPLETIONS_URL,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self._model,
                        "messages": messages,
                        "response_format": {"type": "json_object"},
                        "temperature": 0,
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException:
            raise LLMTimeoutFailure from None
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403}:
                raise LLMConfigurationFailure from None
            raise LLMProviderError from None
        except httpx.RequestError:
            raise LLMProviderError from None

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (IndexError, KeyError, TypeError, ValueError):
            raise LLMProviderError from None

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError
        return content