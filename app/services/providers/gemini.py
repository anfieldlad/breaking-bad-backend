"""
Google Gemini provider implementations (via the google-genai SDK).
"""

from typing import Generator, List

from google import genai
from google.genai import types

from app.core.logging import get_logger
from app.services.providers.base import (
    ChatChunk,
    ChatMessage,
    ChatProvider,
    EmbeddingProvider,
)

logger = get_logger(__name__)


class GeminiChatProvider(ChatProvider):
    """Streaming chat backend backed by Google Gemini."""

    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def stream(
        self,
        system_instruction: str,
        messages: List[ChatMessage],
    ) -> Generator[ChatChunk, None, None]:
        contents = [
            types.Content(
                role="model" if m.role in ("model", "assistant") else "user",
                parts=[types.Part(text=m.text)],
            )
            for m in messages
        ]

        responses = self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
            ),
        )

        for response in responses:
            if not response.candidates:
                continue
            for part in response.candidates[0].content.parts:
                thought = getattr(part, "thought", None)
                text = part.text
                if thought or text:
                    yield ChatChunk(answer=text or None, thought=thought or None)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embedding backend backed by Google Gemini."""

    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def embed(self, text: str, task_type: str) -> List[float]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(task_type=task_type),
        )
        return response.embeddings[0].values
