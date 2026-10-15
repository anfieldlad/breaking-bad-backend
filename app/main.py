"""
FastAPI application factory.

Creates and configures the FastAPI application with all middleware,
routes, and event handlers.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.container import build_services
from app.api.errors import register_exception_handlers
from app.api.middleware import RequestContextMiddleware
from app.api.v1.router import router
from app.core.config import Settings, get_settings
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build long-lived services at startup and release them at shutdown."""
    settings: Settings = app.state.settings
    setup_logging(settings)
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # Fails fast on invalid configuration (e.g. missing provider API key).
    app.state.services = build_services(settings)
    try:
        yield
    finally:
        app.state.services.close()
        logger.info("Application shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        settings: Optional settings override (defaults to environment).

    Returns:
        Configured FastAPI application instance.
    """
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Breaking B.A.D. (Bot Answering Dialogue) - "
            "A RAG chatbot API that ingests PDF documents and answers questions "
            "based on their content using a pluggable LLM backend."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.settings = settings

    # Only needed when browsers call the API directly. Auth uses a header,
    # not cookies, so credentials are not allowed.
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Content-Type", "X-API-Key", "X-Cleanup-Password", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
        )

    # Outermost: every request (incl. CORS preflights) gets an ID and an access log line.
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)
    app.include_router(router)

    return app


# Create application instance
app = create_app()
