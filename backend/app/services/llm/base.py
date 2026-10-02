from typing import Protocol


class LLMProviderError(Exception):
    """A provider failure without user-facing or credential-bearing details."""


class LLMConfigurationFailure(LLMProviderError):
    """The selected provider is missing required local configuration."""


class LLMTimeoutFailure(LLMProviderError):
    """The provider did not respond before the configured deadline."""


class LLMProvider(Protocol):
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        timeout: float | None = None,
    ) -> str: ...