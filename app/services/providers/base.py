"""
Provider-neutral interfaces and data structures for LLM backends.

These abstractions let ChatService and EmbeddingService work against a stable
contract while the concrete provider (Gemini or OpenAI-compatible) is chosen at
runtime from configuration.
"""

from abc import ABC, abstractmethod
from collections.abc import Generator
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """
    A single conversation message in a provider-neutral form.

    Attributes:
        role: Either "user" or "model" (assistant). Providers map this to their
            own role vocabulary.
        text: The message text content.
    """

    role: str
    text: str


@dataclass
class ChatChunk:
    """
    A streamed fragment of a chat response.

    Attributes:
        answer: Visible answer text, if present in this chunk.
        thought: Reasoning/thinking text, if the provider exposes it.
    """

    answer: str | None = None
    thought: str | None = None


class ChatProvider(ABC):
    """Abstract base class for streaming chat completion backends."""

    @abstractmethod
    def stream(
        self,
        system_instruction: str,
        messages: list[ChatMessage],
    ) -> Generator[ChatChunk, None, None]:
        """
        Stream a chat completion.

        Args:
            system_instruction: The system prompt (persona + retrieved context).
            messages: Conversation messages in chronological order.

        Yields:
            ChatChunk fragments as they are produced by the model.
        """
        raise NotImplementedError


class EmbeddingProvider(ABC):
    """Abstract base class for text embedding backends."""

    @abstractmethod
    def embed(self, text: str, task_type: str) -> list[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: The text to embed.
            task_type: A retrieval hint (e.g. RETRIEVAL_DOCUMENT or
                RETRIEVAL_QUERY). Providers that do not support task types
                (such as OpenAI-compatible endpoints) ignore this argument.

        Returns:
            The embedding as a list of floats.
        """
        raise NotImplementedError
