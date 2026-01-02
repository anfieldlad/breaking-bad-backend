"""
Health check endpoint.

Provides a simple endpoint for monitoring and keep-alive purposes.
"""

from fastapi import APIRouter

from app.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the health status of the application. Used for monitoring and keep-alive.",
)
async def health_check() -> HealthResponse:
    """
    Check if the application is running.
    
    Returns:
        HealthResponse indicating the application is awake.
    """
    return HealthResponse(status="awake")
