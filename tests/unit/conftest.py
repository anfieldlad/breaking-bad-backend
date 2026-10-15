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

from app.api.container import Services  # noqa: E402
from app.api.dependencies import get_app_settings, get_services  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.core.exceptions import DatabaseConnectionError  # noqa: E402
from app.main import app  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.repositories.base import DocumentRepositoryBase  # noqa: E402
from app.services.chat_service import ChatService  # noqa: E402
from app.services.embedding_service import EmbeddingService  # noqa: E402
from app.services.ingestion_service import IngestionService  # noqa: E402
from app.services.pdf_service import PDFService  # noqa: E402
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
        self.fail_db = False

    def insert_many(self, documents: list[Document]) -> int:
        self.documents.extend(documents)
        return len(documents)

    def replace_file(self, filename: str, documents: list[Document]) -> int:
        self.documents = [d for d in self.documents if d.filename != filename]
        return self.insert_many(documents)

    def vector_search(self, query_embedding: list[float], limit: int = 5) -> list[Document]:
        if self.fail_db:
            raise RuntimeError("simulated database outage at mongodb://secret-host")
        return self.documents[:limit]

    def count_documents(self) -> int:
        if self.fail_db:
            # Mirrors MongoDocumentRepository's error translation contract.
            raise DatabaseConnectionError() from RuntimeError("outage at mongodb://secret-host")
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
def embedding_service() -> EmbeddingService:
    return EmbeddingService(FakeEmbeddingProvider())


@pytest.fixture
def services(settings, repository, chat_provider, embedding_service) -> Services:
    return Services(
        repository=repository,
        ingestion_service=IngestionService(
            pdf_service=PDFService(settings),
            embedding_service=embedding_service,
            repository=repository,
        ),
        chat_service=ChatService(
            provider=chat_provider,
            repository=repository,
            embedding_service=embedding_service,
            vector_search_limit=settings.vector_search_limit,
        ),
    )


@pytest.fixture
def client(settings, services) -> Iterator[TestClient]:
    app.dependency_overrides = {
        get_app_settings: lambda: settings,
        get_services: lambda: services,
    }
    try:
        # raise_server_exceptions=False: assert on the 500 response clients see.
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides = {}


@pytest.fixture
def auth() -> dict[str, str]:
    return {"X-API-Key": API_KEY}
