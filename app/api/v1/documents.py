"""
Document management endpoints.

Provides cleanup/maintenance operations over the stored document collection.
"""

import hmac
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from app.api.dependencies import APIKeyDep, DocumentRepositoryDep, SettingsDep
from app.core.exceptions import BreakingBadError
from app.core.logging import get_logger
from app.models.schemas import DeleteResponse, ErrorResponse

logger = get_logger(__name__)

router = APIRouter(tags=["Documents"])


@router.get(
    "/documents/count",
    summary="Count Documents",
    description="Return the total number of stored document chunks.",
)
async def count_documents(
    repository: DocumentRepositoryDep,
    _api_key: APIKeyDep,
) -> dict:
    """Return the total number of stored documents."""
    try:
        return {"count": repository.count_documents()}
    except BreakingBadError as e:
        logger.error(f"Count error: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete(
    "/documents",
    response_model=DeleteResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Missing 'filename' or 'all'"},
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        403: {
            "model": ErrorResponse,
            "description": "Invalid/missing cleanup password, or cleanup disabled",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Database error"},
    },
    summary="Cleanup Documents",
    description=(
        "Delete stored document chunks. Provide `filename` to delete a single "
        "file's chunks, or `all=true` to wipe the entire collection. One of the "
        "two is required as a safety guard. The `X-Cleanup-Password` header must "
        "match the server's CLEANUP_PASSWORD; if none is configured, cleanup is "
        "disabled."
    ),
)
async def delete_documents(
    repository: DocumentRepositoryDep,
    settings: SettingsDep,
    _api_key: APIKeyDep,
    filename: Optional[str] = Query(
        None, description="Delete only chunks from this filename"
    ),
    all: bool = Query(
        False, description="Set to true to delete ALL documents in the collection"
    ),
    cleanup_password: Optional[str] = Header(
        None,
        alias="X-Cleanup-Password",
        description="Master password required when configured on the server",
    ),
) -> DeleteResponse:
    """
    Delete documents from the collection.

    Exactly one selector must be provided:
    - `filename`: delete only that file's chunks.
    - `all=true`: delete every document (full cleanup).

    Args:
        repository: The injected document repository.
        _api_key: Verified API key (required for auth).
        filename: Optional filename selector.
        all: When true, deletes all documents.

    Returns:
        DeleteResponse with the number of documents deleted.

    Raises:
        HTTPException: If no selector is given, or on database errors.
    """
    # Master password gate. Fail closed: without a configured password the
    # destructive endpoint is disabled rather than left open.
    if not settings.cleanup_password:
        logger.warning("Cleanup attempt while CLEANUP_PASSWORD is not configured")
        raise HTTPException(
            status_code=403,
            detail="Document cleanup is disabled: no cleanup password is configured.",
        )
    if not hmac.compare_digest(
        (cleanup_password or "").encode(), settings.cleanup_password.encode()
    ):
        logger.warning("Cleanup attempt with invalid/missing password")
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing cleanup password.",
        )

    if not filename and not all:
        raise HTTPException(
            status_code=400,
            detail="Provide 'filename' to delete a file, or 'all=true' to delete everything.",
        )
    if filename and all:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'filename' or 'all=true', not both.",
        )

    try:
        if all:
            deleted = repository.delete_all()
            logger.info(f"Cleanup: deleted all documents ({deleted})")
        else:
            deleted = repository.delete_by_filename(filename)
            logger.info(f"Cleanup: deleted documents for '{filename}' ({deleted})")

        return DeleteResponse(message="Success", deleted_count=deleted)
    except BreakingBadError as e:
        logger.error(f"Delete error: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Unexpected delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
