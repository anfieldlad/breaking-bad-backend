"""Live connectivity tests for the configured LLM providers (chat + embedding)."""

import pytest

pytestmark = pytest.mark.integration


def test_embedding_provider_live(settings):
    from app.services.providers import get_embedding_provider

    provider = get_embedding_provider(settings)
    vec = provider.embed("hello world", "RETRIEVAL_QUERY")

    assert isinstance(vec, list)
    assert len(vec) > 0
    assert all(isinstance(x, (int, float)) for x in vec[:5])


def test_embedding_query_vs_document_same_dim(settings):
    from app.services.providers import get_embedding_provider

    provider = get_embedding_provider(settings)
    q = provider.embed("a query", "RETRIEVAL_QUERY")
    d = provider.embed("a document", "RETRIEVAL_DOCUMENT")
    assert len(q) == len(d)


def test_chat_provider_live(settings):
    from app.services.providers import get_chat_provider
    from app.services.providers.base import ChatMessage

    provider = get_chat_provider(settings)
    answer = "".join(
        chunk.answer or ""
        for chunk in provider.stream(
            "You are a terse test bot.",
            [ChatMessage(role="user", text="Reply with the single word: pong")],
        )
    )
    assert answer.strip(), "chat provider returned no answer text"
