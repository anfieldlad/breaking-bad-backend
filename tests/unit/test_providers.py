"""Unit tests for provider response parsing (no network)."""

from google.genai import types

from app.services.providers.base import ChatChunk
from app.services.providers.gemini import chunks_from_response


def _response(*parts: types.Part, content: bool = True) -> types.GenerateContentResponse:
    candidate = types.Candidate(
        content=types.Content(role="model", parts=list(parts)) if content else None
    )
    return types.GenerateContentResponse(candidates=[candidate])


def test_gemini_separates_thoughts_from_answer():
    response = _response(
        types.Part(text="Let me think.", thought=True),
        types.Part(text="The answer."),
    )

    assert list(chunks_from_response(response)) == [
        ChatChunk(thought="Let me think."),
        ChatChunk(answer="The answer."),
    ]


def test_gemini_skips_empty_parts_and_contentless_chunks():
    assert list(chunks_from_response(_response(types.Part(text="")))) == []
    assert list(chunks_from_response(_response(content=False))) == []
    assert list(chunks_from_response(types.GenerateContentResponse(candidates=[]))) == []
