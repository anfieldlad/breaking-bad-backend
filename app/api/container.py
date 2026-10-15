"""
Application service container.

Long-lived objects (database client, LLM clients, services) are built once
at startup, stored on `app.state`, and closed at shutdown. Request handlers
receive them through the dependencies in `app.api.dependencies`.
"""

from dataclasses import dataclass

from app.core.config import Settings
from app.repositories.base import DocumentRepositoryBase
from app.repositories.document_repository import MongoDocumentRepository
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.pdf_service import PDFService
from app.services.providers import get_chat_provider, get_embedding_provider


@dataclass
class Services:
    repository: DocumentRepositoryBase
    ingestion_service: IngestionService
    chat_service: ChatService

    def close(self) -> None:
        self.repository.close()


def build_services(settings: Settings) -> Services:
    """Wire up the production object graph from settings."""
    repository = MongoDocumentRepository(settings)
    embedding_service = EmbeddingService(get_embedding_provider(settings))
    return Services(
        repository=repository,
        ingestion_service=IngestionService(
            pdf_service=PDFService(settings),
            embedding_service=embedding_service,
            repository=repository,
        ),
        chat_service=ChatService(
            provider=get_chat_provider(settings),
            repository=repository,
            embedding_service=embedding_service,
            vector_search_limit=settings.vector_search_limit,
        ),
    )
