"""
Google Gemini provider implementations (via the google-genai SDK).
"""

from typing import Generator, Iterator, List

from google import genai
from google.genai import types

from app.services.providers.base import (
    ChatChunk,
    ChatMessage,
    ChatProvider,
    EmbeddingProvider,
)


def chunks_from_response(response: types.GenerateContentResponse) -> Iterator[ChatChunk]:
    """
    Convert one streamed Gemini response into provider-neutral chunks.

    Gemini marks reasoning parts with the boolean `part.thought`; the text of
    both reasoning and answer parts is in `part.text`.
    """
    if not response.candidates:
        return
    content = response.candidates[0].content
    # The final chunk of a stream may carry only a finish reason.
    if content is None or not content.parts:
        return
    for part in content.parts:
        if not part.text:
            continue
        if part.thought:
            yield ChatChunk(thought=part.text)
        else:
            yield ChatChunk(answer=part.text)


class GeminiChatProvider(ChatProvider):
    """Streaming chat backend backed by Google Gemini."""

    def __init__(self, api_key: str, model: str, include_thoughts: bool = True):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.include_thoughts = include_thoughts

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
                thinking_config=(
                    types.ThinkingConfig(include_thoughts=True)
                    if self.include_thoughts
                    else None
                ),
            ),
        )

        for response in responses:
            yield from chunks_from_response(response)


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
