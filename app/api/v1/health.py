"""
Health check endpoints.

- `/health`: liveness. The process is up (also used as a keep-alive).
- `/health/ready`: readiness. Dependencies (the database) are reachable;
  use it for load balancer / orchestrator health checks.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.dependencies import DocumentRepositoryDep
from app.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness Check",
    description="Returns 200 while the process is running. Used for monitoring and keep-alive.",
)
async def health_check() -> HealthResponse:
    return HealthResponse(status="awake")


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "A dependency is unavailable"}},
    summary="Readiness Check",
    description="Returns 200 when the database is reachable, 503 otherwise.",
)
def readiness_check(repository: DocumentRepositoryDep) -> HealthResponse | JSONResponse:
    if repository.ping():
        return HealthResponse(status="ready")
    return JSONResponse(status_code=503, content={"status": "unavailable"})
