"""
Exception handlers that map application errors to HTTP responses.

Routes and services raise `BreakingBadError` subclasses; this module turns
them into `{"detail": ...}` responses in one place instead of per-route
try/except blocks.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import BreakingBadError
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _handle_app_error(request: Request, exc: BreakingBadError) -> JSONResponse:
    log = logger.error if exc.status_code >= 500 else logger.warning
    log(
        "%s on %s %s: %s",
        type(exc).__name__,
        request.method,
        request.url.path,
        exc.detail,
        exc_info=exc.__cause__ is not None and exc.status_code >= 500,
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BreakingBadError, _handle_app_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
