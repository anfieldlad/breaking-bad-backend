"""
Factory functions that build the configured chat/embedding providers.

Selection is driven by Settings.chat_provider and Settings.embedding_provider,
each independently set to "gemini" or "openai".
"""

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.services.providers.base import ChatProvider, EmbeddingProvider
from app.services.providers.gemini import (
    GeminiChatProvider,
    GeminiEmbeddingProvider,
)
from app.services.providers.openai_compat import (
    OpenAIChatProvider,
    OpenAIEmbeddingProvider,
)


def get_chat_provider(settings: Settings) -> ChatProvider:
    """Build the chat provider selected by settings.chat_provider."""
    provider = settings.chat_provider

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY is required when CHAT_PROVIDER=gemini"
            )
        return GeminiChatProvider(
            settings.gemini_api_key,
            settings.chat_model,
            include_thoughts=settings.gemini_include_thoughts,
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is required when CHAT_PROVIDER=openai"
            )
        return OpenAIChatProvider(
            settings.openai_api_key,
            settings.openai_base_url,
            settings.chat_model,
        )

    raise ConfigurationError(f"Unknown CHAT_PROVIDER: {settings.chat_provider!r}")


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build the embedding provider selected by settings.embedding_provider."""
    provider = settings.embedding_provider

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY is required when EMBEDDING_PROVIDER=gemini"
            )
        return GeminiEmbeddingProvider(
            settings.gemini_api_key, settings.embedding_model
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai"
            )
        return OpenAIEmbeddingProvider(
            settings.openai_api_key,
            settings.openai_base_url,
            settings.embedding_model,
        )

    raise ConfigurationError(
        f"Unknown EMBEDDING_PROVIDER: {settings.embedding_provider!r}"
    )
