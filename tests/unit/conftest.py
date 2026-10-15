"""
Fixtures for the offline unit test suite.

Unit tests never touch MongoDB or an LLM endpoint: the repository and the
LLM providers are replaced with in-memory fakes via FastAPI dependency
overrides, so the suite runs anywhere (CI included) without a `.env`.
"""

import os
from collections.abc import Iterator

import pytest

# The app reads settings at import time; provide harmless placeholders so the
# import succeeds without a `.env`. Real values (if present) take precedence.
os.environ.setdefault("MONGO_URI", "mongodb://unit-tests.invalid:27017")
os.environ.setdefault("API_KEY", "unit-test-key")

from fastapi.testclient import TestClient  # noqa: E402

from app.api import dependencies  # noqa: E402
from app.core.config import Settings, get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.repositories.base import DocumentRepositoryBase  # noqa: E402
from app.services.chat_service import ChatService  # noqa: E402
from app.services.providers.base import (  # noqa: E402
    ChatChunk,
    ChatProvider,
    EmbeddingProvider,
)

API_KEY = "unit-test-key"
CLEANUP_PASSWORD = "unit-test-cleanup"


class FakeRepository(DocumentRepositoryBase):
    """In-memory document store."""

    def __init__(self) -> None:
        self.documents: list[Document] = []
        self.fail_search = False

    def insert_many(self, documents: list[Document]) -> int:
        self.documents.extend(documents)
        return len(documents)

    def vector_search(self, query_embedding: list[float], limit: int = 5) -> list[Document]:
        if self.fail_search:
            raise RuntimeError("simulated database outage at mongodb://secret-host")
        return self.documents[:limit]

    def count_documents(self) -> int:
        return len(self.documents)

    def delete_by_filename(self, filename: str) -> int:
        before = len(self.documents)
        self.documents = [d for d in self.documents if d.filename != filename]
        return before - len(self.documents)

    def delete_all(self) -> int:
        deleted = len(self.documents)
        self.documents = []
        return deleted


class FakeEmbeddingProvider(EmbeddingProvider):
    def embed(self, text: str, task_type: str) -> list[float]:
        return [float(len(text)), 1.0, 0.0]


class FakeChatProvider(ChatProvider):
    """Streams a scripted list of chunks, optionally failing afterwards."""

    def __init__(self) -> None:
        self.chunks: list[ChatChunk] = [ChatChunk(answer="Hello"), ChatChunk(answer=" world")]
        self.fail_after_chunks = False
        self.calls: list[tuple[str, list]] = []

    def stream(self, system_instruction, messages):
        self.calls.append((system_instruction, messages))
        yield from self.chunks
        if self.fail_after_chunks:
            raise RuntimeError("simulated provider failure with internal details")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        mongo_uri="mongodb://unit-tests.invalid:27017",
        api_key=API_KEY,
        cleanup_password=CLEANUP_PASSWORD,
        gemini_api_key="unit-test-gemini-key",
    )


@pytest.fixture
def repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def chat_provider() -> FakeChatProvider:
    return FakeChatProvider()


@pytest.fixture
def embedding_service(settings):
    from app.services.embedding_service import EmbeddingService

    service = EmbeddingService(settings)
    service.provider = FakeEmbeddingProvider()
    return service


@pytest.fixture
def client(settings, repository, chat_provider, embedding_service) -> Iterator[TestClient]:
    def _chat_service() -> ChatService:
        service = ChatService(
            settings=settings,
            repository=repository,
            embedding_service=embedding_service,
        )
        service.provider = chat_provider
        return service

    app.dependency_overrides = {
        get_settings: lambda: settings,
        dependencies.get_document_repository: lambda: repository,
        dependencies.get_embedding_service: lambda: embedding_service,
        dependencies.get_chat_service: _chat_service,
    }
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides = {}


@pytest.fixture
def auth() -> dict[str, str]:
    return {"X-API-Key": API_KEY}
