"""
Custom middleware for the FastAPI application.

Provides error handling middleware for consistent error responses.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import BreakingBadError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling exceptions and returning consistent error responses.
    
    Catches BreakingBadError exceptions and converts them to appropriate
    JSON responses with the correct status codes.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and handle any exceptions.
        
        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.
        
        Returns:
            The response from the next handler or an error response.
        """
        try:
            response = await call_next(request)
            return response
        except BreakingBadError as e:
            logger.error(
                f"Application error: {e.detail}",
                extra={"status_code": e.status_code, "path": request.url.path},
            )
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error: {e}",
                extra={"path": request.url.path},
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "An unexpected error occurred"},
            )
