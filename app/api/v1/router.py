"""
API v1 router aggregation.

Combines all v1 endpoints under a single router with /api prefix.
"""

from fastapi import APIRouter

from app.api.v1 import chat, health, ingest

# Create the main API router
router = APIRouter()

# Include health endpoint at root level (no /api prefix needed)
router.include_router(health.router)

# Create API router for authenticated endpoints
api_router = APIRouter(prefix="/api")
api_router.include_router(ingest.router)
api_router.include_router(chat.router)

# Include API router
router.include_router(api_router)
