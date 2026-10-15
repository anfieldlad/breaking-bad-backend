"""End-to-end RAG test: ingest a PDF, then retrieve + answer over it."""

import json
import time

import pytest

pytestmark = pytest.mark.integration


def _chat(client, auth, question):
    """POST /api/chat and parse the SSE stream into (sources, answer)."""
    resp = client.post(
        "/api/chat",
        headers=auth,
        json={"question": question, "history": []},
    )
    assert resp.status_code == 200, resp.text

    sources, answer = [], ""
    for line in resp.text.splitlines():
        if not line.startswith("data: "):
            continue
        payload = json.loads(line[len("data: "):])
        if isinstance(payload.get("sources"), list):
            sources = payload["sources"]
        answer += payload.get("answer", "")
    return sources, answer


def test_rag_end_to_end(client, auth, ingest, vector_index_ready):
    fact = "The Heisenberg compound has a measured purity of 99.1 percent."
    filename, chunks = ingest("rag", "RAG end-to-end test document.", fact)
    assert chunks >= 1

    question = "What is the exact purity of the Heisenberg compound?"

    # Atlas vector search is eventually consistent: a freshly ingested doc may
    # take a few seconds to become searchable. Retry briefly.
    sources, answer = [], ""
    deadline = time.time() + 45
    while time.time() < deadline:
        sources, answer = _chat(client, auth, question)
        if filename in sources:
            break
        time.sleep(5)

    assert filename in sources, f"ingested doc not retrieved; sources={sources}"
    assert "99.1" in answer, f"answer missing the grounded fact; answer={answer!r}"
