"""
Document management endpoints.

Provides cleanup/maintenance operations over the stored document collection.
"""

import hmac

from fastapi import APIRouter, Header, HTTPException, Query

from app.api.dependencies import APIKeyDep, DocumentRepositoryDep, SettingsDep
from app.core.logging import get_logger
from app.models.schemas import CountResponse, DeleteResponse, ErrorResponse

logger = get_logger(__name__)

router = APIRouter(tags=["Documents"])


# Handlers are sync (`def`) so FastAPI runs the blocking database calls in
# its threadpool instead of on the event loop.


@router.get(
    "/documents/count",
    response_model=CountResponse,
    summary="Count Documents",
    description="Return the total number of stored document chunks.",
)
def count_documents(
    repository: DocumentRepositoryDep,
    _api_key: APIKeyDep,
) -> CountResponse:
    """Return the total number of stored documents."""
    return CountResponse(count=repository.count_documents())


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
def delete_documents(
    repository: DocumentRepositoryDep,
    settings: SettingsDep,
    _api_key: APIKeyDep,
    filename: str | None = Query(None, description="Delete only chunks from this filename"),
    all: bool = Query(False, description="Set to true to delete ALL documents in the collection"),
    cleanup_password: str | None = Header(
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

    if all:
        deleted = repository.delete_all()
        logger.info("Cleanup: deleted all documents (%d)", deleted)
    else:
        deleted = repository.delete_by_filename(filename)
        logger.info("Cleanup: deleted documents for %s (%d)", filename, deleted)

    return DeleteResponse(message="Success", deleted_count=deleted)
