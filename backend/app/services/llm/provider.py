from app.core.config import Settings
from app.core.errors import AIConfigurationError
from app.services.llm.base import LLMConfigurationFailure, LLMProvider
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.openai_provider import OpenAIChatCompletionsProvider


def create_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "ollama":
        try:
            return OllamaProvider(settings)
        except LLMConfigurationFailure:
            raise AIConfigurationError from None
    if settings.llm_provider != "openai":
        raise AIConfigurationError
    try:
        return OpenAIChatCompletionsProvider(settings)
    except LLMConfigurationFailure:
        raise AIConfigurationError from None