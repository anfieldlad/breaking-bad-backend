"""
FastAPI application factory.

Creates and configures the FastAPI application with all middleware,
routes, and event handlers.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the application.
    """
    # Startup
    setup_logging()
    settings = get_settings()
    logger.info(
        f"Starting {settings.app_name} v{settings.app_version}",
        extra={"debug": settings.debug},
    )
    
    yield
    
    # Shutdown
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Breaking B.A.D. (Bot Answering Dialogue) - "
            "A RAG chatbot API that ingests PDF documents and answers questions "
            "based on their content using Google Gemini AI."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Configure CORS
    # NOTE: In production, replace "*" with specific frontend URLs
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure to frontend URL in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(router)
    
    return app


# Create application instance
app = create_app()
