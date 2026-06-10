"""
Shared pytest fixtures for the functional test suite.

These tests run against the LIVE services configured in your `.env`
(MongoDB Atlas + the OpenAI-compatible / Gemini endpoint). They are designed to
be safe to run repeatedly:

* Every document created by a test uses the `TEST_PREFIX` filename prefix.
* An autouse fixture removes any leftover prefixed documents before and after
  each test, so the suite never pollutes (or relies on) real data.
* Destructive operations (e.g. `?all=true`) refuse to run when the collection
  contains real, non-test documents.

Requirements: a populated `.env` and network access. Install test deps with
`pip install -r requirements-dev.txt`.
"""

import io
import time

import pytest

# Filename prefix that marks a document as test-owned (safe to delete).
TEST_PREFIX = "__pytest__"


@pytest.fixture(scope="session")
def settings():
    """Load application settings from the environment (.env)."""
    from app.core.config import get_settings

    return get_settings()


@pytest.fixture(scope="session")
def client():
    """A TestClient bound to the real app (real services behind it)."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth(settings):
    """Auth header for protected endpoints."""
    return {"X-API-Key": settings.api_key}


@pytest.fixture(scope="session")
def cleanup_headers(settings):
    """Auth header plus the cleanup master password (if one is configured)."""
    headers = {"X-API-Key": settings.api_key}
    if settings.cleanup_password:
        headers["X-Cleanup-Password"] = settings.cleanup_password
    return headers


@pytest.fixture(scope="session")
def mongo(settings):
    """Direct handle to the live collection (for verification & cleanup)."""
    from pymongo import MongoClient

    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=10000)
    try:
        collection = client[settings.db_name][settings.collection_name]
        yield collection
    finally:
        client.close()


@pytest.fixture
def pdf_factory():
    """Return a function that builds a one-page PDF (bytes) from text lines."""
    pytest.importorskip("reportlab", reason="reportlab is needed to build test PDFs")
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    def _make(*lines: str) -> bytes:
        buf = io.BytesIO()
        cv = canvas.Canvas(buf, pagesize=letter)
        y = 720
        for line in lines or ("Test document",):
            cv.drawString(72, y, line)
            y -= 24
        cv.showPage()
        cv.save()
        return buf.getvalue()

    return _make


@pytest.fixture
def ingest(client, auth, pdf_factory):
    """Helper to ingest a PDF; returns (filename, chunks_stored)."""

    def _ingest(name: str, *lines: str):
        filename = f"{TEST_PREFIX}_{name}.pdf"
        resp = client.post(
            "/api/ingest",
            headers=auth,
            files={"file": (filename, pdf_factory(*lines), "application/pdf")},
        )
        assert resp.status_code == 200, resp.text
        return filename, resp.json()["chunks_stored"]

    return _ingest


@pytest.fixture(autouse=True)
def _cleanup_test_docs(mongo):
    """Remove test-owned documents before and after every test."""
    selector = {"filename": {"$regex": f"^{TEST_PREFIX}"}}
    mongo.delete_many(selector)
    yield
    mongo.delete_many(selector)


@pytest.fixture(scope="session")
def embedding_dim(settings):
    """Live embedding dimension, derived by probing the configured provider."""
    from app.services.providers import get_embedding_provider

    provider = get_embedding_provider(settings)
    return len(provider.embed("dimension probe", "RETRIEVAL_QUERY"))


@pytest.fixture(scope="session")
def vector_index_ready(settings, mongo, embedding_dim):
    """
    Ensure the Atlas vector index exists and is queryable.

    Creates it (idempotently) with the live embedding dimension if missing,
    then waits until queryable. Skips the dependent test if the index cannot be
    made ready or has a mismatched dimension.
    """
    from pymongo.operations import SearchIndexModel

    name = settings.vector_index_name

    def _find():
        for idx in mongo.list_search_indexes():
            if idx["name"] == name:
                return idx
        return None

    if _find() is None:
        mongo.create_search_index(
            model=SearchIndexModel(
                definition={
                    "fields": [
                        {
                            "type": "vector",
                            "path": "embedding",
                            "numDimensions": embedding_dim,
                            "similarity": "cosine",
                        }
                    ]
                },
                name=name,
                type="vectorSearch",
            )
        )

    deadline = time.time() + 180
    while time.time() < deadline:
        idx = _find()
        if idx and idx.get("queryable"):
            dims = [
                f.get("numDimensions")
                for f in idx.get("latestDefinition", {}).get("fields", [])
                if f.get("type") == "vector"
            ]
            if dims and dims[0] != embedding_dim:
                pytest.skip(
                    f"vector index '{name}' has {dims[0]} dims but the embedding "
                    f"model produces {embedding_dim}; recreate the index to test RAG."
                )
            return True
        time.sleep(5)

    pytest.skip(f"vector index '{name}' did not become queryable in time")
