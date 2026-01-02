"""
Custom exceptions for the application.

Provides a hierarchy of exceptions with HTTP status code mapping
for consistent error handling across the API.
"""

from typing import Optional


class BreakingBadError(Exception):
    """Base exception for all application errors."""

    status_code: int = 500
    detail: str = "An unexpected error occurred"

    def __init__(self, detail: Optional[str] = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class ConfigurationError(BreakingBadError):
    """Raised when there's a configuration issue."""

    status_code = 500
    detail = "Configuration error"


class PDFProcessingError(BreakingBadError):
    """Raised when PDF processing fails."""

    status_code = 400
    detail = "Failed to process PDF file"


class InvalidFileTypeError(BreakingBadError):
    """Raised when an unsupported file type is uploaded."""

    status_code = 400
    detail = "Only PDF files are supported"


class EmptyPDFError(BreakingBadError):
    """Raised when a PDF contains no extractable text."""

    status_code = 400
    detail = "PDF contains no extractable text"


class EmbeddingError(BreakingBadError):
    """Raised when embedding generation fails."""

    status_code = 502
    detail = "Failed to generate embeddings"


class VectorSearchError(BreakingBadError):
    """Raised when vector search fails."""

    status_code = 502
    detail = "Vector search failed"


class ChatGenerationError(BreakingBadError):
    """Raised when chat response generation fails."""

    status_code = 502
    detail = "Failed to generate chat response"


class DocumentNotFoundError(BreakingBadError):
    """Raised when requested documents are not found."""

    status_code = 404
    detail = "No documents found"


class AuthenticationError(BreakingBadError):
    """Raised when API key validation fails."""

    status_code = 401
    detail = "Invalid or missing API key"


class DatabaseConnectionError(BreakingBadError):
    """Raised when database connection fails."""

    status_code = 503
    detail = "Database connection failed"
