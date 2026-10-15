"""
Pydantic schemas for API request and response validation.

Provides type-safe data validation for all API endpoints.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Request size limits: bound prompt size (and therefore LLM cost/latency).
MAX_QUESTION_CHARS = 4_000
MAX_HISTORY_ITEMS = 50
MAX_HISTORY_TEXT_CHARS = 20_000


# ----- Chat Schemas -----


class HistoryPart(BaseModel):
    """A single part of a message in the chat history."""

    text: str = Field(..., max_length=MAX_HISTORY_TEXT_CHARS)


class HistoryItem(BaseModel):
    """
    A single message in the conversation history.

    Attributes:
        role: The role of the message sender ('user' or 'model').
        parts: List of message parts (typically containing text).
    """

    role: Literal["user", "model"] = Field(..., description="Role: 'user' or 'model'")
    parts: list[HistoryPart] = Field(..., max_length=10)


class ChatRequest(BaseModel):
    """
    Request body for the chat endpoint.

    Attributes:
        question: The user's question to be answered.
        history: Optional conversation history for multi-turn chat.
    """

    question: str = Field(
        ...,
        min_length=1,
        max_length=MAX_QUESTION_CHARS,
        description="The question to ask",
    )
    history: list[HistoryItem] = Field(
        default_factory=list,
        max_length=MAX_HISTORY_ITEMS,
        description="Previous conversation history for context (oldest first)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "What is this document about?",
                    "history": [
                        {"role": "user", "parts": [{"text": "Hello!"}]},
                        {"role": "model", "parts": [{"text": "Hi! I'm Breaking B.A.D."}]},
                    ],
                }
            ]
        }
    }


# ----- Ingest Schemas -----


class IngestResponse(BaseModel):
    """Response body for successful PDF ingestion."""

    message: str = Field(default="Success")
    chunks_stored: int = Field(..., description="Number of chunks/pages stored")


# ----- Document Management Schemas -----


class CountResponse(BaseModel):
    """Response body for the document count endpoint."""

    count: int = Field(..., description="Number of stored document chunks")


class DeleteResponse(BaseModel):
    """Response body for document deletion/cleanup."""

    message: str = Field(default="Success")
    deleted_count: int = Field(..., description="Number of documents deleted")


# ----- Health Schemas -----


class HealthResponse(BaseModel):
    """Response body for health check endpoint."""

    status: str = Field(default="awake")


# ----- Error Schemas -----


class ErrorResponse(BaseModel):
    """Standard error response format."""

    detail: str = Field(..., description="Error message")


class ValidationErrorDetail(BaseModel):
    """Detail of a validation error."""

    loc: list[str] = Field(..., description="Location of the error")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """Response for validation errors (422)."""

    detail: list[ValidationErrorDetail]
