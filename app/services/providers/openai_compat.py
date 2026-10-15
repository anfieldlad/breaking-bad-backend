"""
OpenAI-compatible provider implementations (via the openai SDK).

Works with the official OpenAI API as well as any endpoint that implements the
OpenAI Chat Completions / Embeddings API, including self-hosted servers such as
vLLM, Ollama, LM Studio, Together, and Groq. The endpoint is selected via the
base_url argument.
"""

from collections.abc import Generator

from openai import OpenAI

from app.services.providers.base import (
    ChatChunk,
    ChatMessage,
    ChatProvider,
    EmbeddingProvider,
)


class OpenAIChatProvider(ChatProvider):
    """Streaming chat backend for any OpenAI-compatible endpoint."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def stream(
        self,
        system_instruction: str,
        messages: list[ChatMessage],
    ) -> Generator[ChatChunk, None, None]:
        oai_messages = [{"role": "system", "content": system_instruction}]
        for m in messages:
            role = "assistant" if m.role in ("model", "assistant") else "user"
            oai_messages.append({"role": role, "content": m.text})

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=oai_messages,
            stream=True,
        )

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                continue
            content = getattr(delta, "content", None)
            # Some OpenAI-compatible providers (e.g. Qwen, DeepSeek) expose
            # chain-of-thought separately as `reasoning_content`.
            thought = getattr(delta, "reasoning_content", None)
            if content or thought:
                yield ChatChunk(answer=content or None, thought=thought or None)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding backend for any OpenAI-compatible endpoint."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def embed(self, text: str, task_type: str) -> list[float]:
        # OpenAI-compatible embeddings have no task_type concept; it is ignored.
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding
