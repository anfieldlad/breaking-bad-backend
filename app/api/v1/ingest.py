"""
PDF ingestion endpoint.

Handles PDF file uploads and processing into the vector database.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.dependencies import APIKeyDep, IngestionServiceDep
from app.core.exceptions import BreakingBadError
from app.core.logging import get_logger
from app.models.schemas import ErrorResponse, IngestResponse

logger = get_logger(__name__)

router = APIRouter(tags=["Ingestion"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file type or empty PDF"},
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        502: {"model": ErrorResponse, "description": "External service error"},
    },
    summary="Ingest PDF Document",
    description="Upload and process a PDF file. Extracts text, generates embeddings, and stores in the vector database.",
)
async def ingest_pdf(
    ingestion_service: IngestionServiceDep,
    _api_key: APIKeyDep,
    file: UploadFile = File(..., description="PDF file to upload and process"),
) -> IngestResponse:
    """
    Upload and process a PDF document.
    
    The PDF is processed page by page (up to 20 pages), with each page
    becoming a separate document chunk in the vector database.
    
    Args:
        ingestion_service: The injected ingestion service.
        _api_key: Verified API key (unused, but required for auth).
        file: The uploaded PDF file.
    
    Returns:
        IngestResponse with the number of chunks stored.
    
    Raises:
        HTTPException: On processing errors.
    """
    try:
        chunks_stored = await ingestion_service.ingest_pdf(file)
        return IngestResponse(message="Success", chunks_stored=chunks_stored)
    except BreakingBadError as e:
        logger.error(f"Ingestion error: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Unexpected ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
