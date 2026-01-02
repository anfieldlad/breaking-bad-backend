"""
FastAPI dependency injection functions.

Provides dependency factories for services, repositories, and authentication,
following the Dependency Inversion Principle.
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.repositories.document_repository import MongoDocumentRepository
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.pdf_service import PDFService

logger = get_logger(__name__)

# Type alias for dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]

# API Key header definition
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ----- Singleton instances (lazy initialization) -----

_document_repository: Optional[MongoDocumentRepository] = None
_embedding_service: Optional[EmbeddingService] = None
_pdf_service: Optional[PDFService] = None


# ----- Repository Dependencies -----


def get_document_repository() -> MongoDocumentRepository:
    """
    Get the document repository instance (singleton).
    
    Uses lazy initialization to ensure a single instance is reused,
    maintaining database connection pooling.
    """
    global _document_repository
    if _document_repository is None:
        settings = get_settings()
        _document_repository = MongoDocumentRepository(settings)
    return _document_repository


# ----- Service Dependencies -----


def get_embedding_service() -> EmbeddingService:
    """Get the embedding service instance (singleton)."""
    global _embedding_service
    if _embedding_service is None:
        settings = get_settings()
        _embedding_service = EmbeddingService(settings)
    return _embedding_service


def get_pdf_service() -> PDFService:
    """Get the PDF service instance (singleton)."""
    global _pdf_service
    if _pdf_service is None:
        settings = get_settings()
        _pdf_service = PDFService(settings)
    return _pdf_service


def get_ingestion_service(
    pdf_service: PDFService = Depends(get_pdf_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    repository: MongoDocumentRepository = Depends(get_document_repository),
) -> IngestionService:
    """Get the ingestion service instance."""
    return IngestionService(
        pdf_service=pdf_service,
        embedding_service=embedding_service,
        repository=repository,
    )


def get_chat_service(
    repository: MongoDocumentRepository = Depends(get_document_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> ChatService:
    """Get the chat service instance."""
    settings = get_settings()
    return ChatService(
        settings=settings,
        repository=repository,
        embedding_service=embedding_service,
    )


# ----- Authentication Dependencies -----


async def verify_api_key(
    api_key: str = Security(api_key_header),
) -> str:
    """
    Verify the API key from the request header.
    
    Args:
        api_key: The API key from the X-API-Key header.
    
    Returns:
        The verified API key.
    
    Raises:
        HTTPException: If the API key is missing or invalid.
    """
    settings = get_settings()
    
    if api_key is None:
        logger.warning("API request without API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
        )
    
    if api_key != settings.api_key:
        logger.warning("API request with invalid API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    return api_key


# Type aliases for cleaner dependency injection
DocumentRepositoryDep = Annotated[
    MongoDocumentRepository, Depends(get_document_repository)
]
EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
PDFServiceDep = Annotated[PDFService, Depends(get_pdf_service)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
APIKeyDep = Annotated[str, Depends(verify_api_key)]
