"""
FastAPI dependency injection functions.

Services are created once at startup (see `app.api.container`) and exposed
to routes through these dependencies, so tests can swap them via
`app.dependency_overrides[get_services]`.
"""

import hmac
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from app.api.container import Services
from app.core.config import Settings
from app.core.logging import get_logger
from app.repositories.base import DocumentRepositoryBase
from app.services.chat_service import ChatService
from app.services.ingestion_service import IngestionService

logger = get_logger(__name__)


def get_app_settings(request: Request) -> Settings:
    """Return the settings the application was created with."""
    return request.app.state.settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_services(request: Request) -> Services:
    """Return the service container built during application startup."""
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(get_services)]


def get_document_repository(services: ServicesDep) -> DocumentRepositoryBase:
    return services.repository


def get_ingestion_service(services: ServicesDep) -> IngestionService:
    return services.ingestion_service


def get_chat_service(services: ServicesDep) -> ChatService:
    return services.chat_service


async def verify_api_key(
    settings: SettingsDep,
    api_key: Optional[str] = Security(api_key_header),
) -> str:
    """
    Verify the API key from the X-API-Key header.

    Raises:
        HTTPException: 401 if the API key is missing or invalid.
    """
    if api_key is None:
        logger.warning("API request without API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
        )

    if not hmac.compare_digest(api_key.encode(), settings.api_key.encode()):
        logger.warning("API request with invalid API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return api_key


DocumentRepositoryDep = Annotated[DocumentRepositoryBase, Depends(get_document_repository)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
APIKeyDep = Annotated[str, Depends(verify_api_key)]
