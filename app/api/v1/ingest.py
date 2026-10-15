"""
PDF ingestion endpoint.

Handles PDF file uploads and processing into the vector database.
"""

from fastapi import APIRouter, File, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.dependencies import APIKeyDep, IngestionServiceDep, SettingsDep
from app.core.exceptions import FileTooLargeError
from app.models.schemas import ErrorResponse, IngestResponse

router = APIRouter(tags=["Ingestion"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file type or empty PDF"},
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        413: {"model": ErrorResponse, "description": "File exceeds the upload limit"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        502: {"model": ErrorResponse, "description": "External service error"},
        503: {"model": ErrorResponse, "description": "Database error"},
    },
    summary="Ingest PDF Document",
    description=(
        "Upload and process a PDF file. Extracts text, generates embeddings, and "
        "stores them in the vector database. Re-uploading a file with the same "
        "name replaces its previous chunks."
    ),
)
async def ingest_pdf(
    ingestion_service: IngestionServiceDep,
    settings: SettingsDep,
    _api_key: APIKeyDep,
    file: UploadFile = File(..., description="PDF file to upload and process"),
) -> IngestResponse:
    """
    Upload and process a PDF document.

    Each page (up to MAX_PAGES_PER_PDF) becomes a separate document chunk.
    """
    # Read one byte past the limit to detect oversized uploads.
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise FileTooLargeError(f"File exceeds the {settings.max_upload_mb} MB upload limit")

    # Parsing, embedding and storage are blocking; keep them off the event loop.
    chunks_stored = await run_in_threadpool(
        ingestion_service.ingest_pdf, content, file.filename or "unknown.pdf"
    )
    return IngestResponse(message="Success", chunks_stored=chunks_stored)
