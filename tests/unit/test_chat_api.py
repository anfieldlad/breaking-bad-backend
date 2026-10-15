"""Unit tests for the streaming chat endpoint."""

from app.models.document import Document
from tests.unit.sse import parse_sse


def test_chat_requires_api_key(client):
    resp = client.post("/api/chat", json={"question": "hi"})
    assert resp.status_code == 401


def test_chat_streams_sources_then_answer(client, auth, repository):
    repository.insert_many(
        [Document(text="Blue sky.", embedding=[1.0], filename="a.pdf", chunk_id=0)]
    )

    resp = client.post("/api/chat", json={"question": "hi"}, headers=auth)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(resp.text)
    assert events[0] == {"sources": ["a.pdf"]}
    assert "".join(e.get("answer", "") for e in events) == "Hello world"
    assert not any("error" in e for e in events)


def test_chat_reports_retrieval_failure_as_error_event(client, auth, repository):
    repository.fail_search = True

    resp = client.post("/api/chat", json={"question": "hi"}, headers=auth)

    assert resp.status_code == 200
    events = parse_sse(resp.text)
    assert events == [{"error": "Failed to generate chat response"}]
    assert "secret-host" not in resp.text


def test_chat_reports_mid_stream_failure_after_partial_answer(
    client, auth, chat_provider
):
    chat_provider.fail_after_chunks = True

    resp = client.post("/api/chat", json={"question": "hi"}, headers=auth)

    events = parse_sse(resp.text)
    assert "".join(e.get("answer", "") for e in events) == "Hello world"
    assert events[-1] == {"error": "Failed to generate chat response"}
    assert "internal details" not in resp.text
