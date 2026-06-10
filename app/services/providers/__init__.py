"""
LLM provider abstraction.

Provides a unified interface over different LLM backends (Google Gemini and
any OpenAI-compatible endpoint) so the rest of the application does not depend
on a specific vendor SDK.
"""

from app.services.providers.base import (
    ChatChunk,
    ChatMessage,
    ChatProvider,
    EmbeddingProvider,
)
from app.services.providers.factory import (
    get_chat_provider,
    get_embedding_provider,
)

__all__ = [
    "ChatChunk",
    "ChatMessage",
    "ChatProvider",
    "EmbeddingProvider",
    "get_chat_provider",
    "get_embedding_provider",
]
