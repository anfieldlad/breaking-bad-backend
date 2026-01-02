"""
Pydantic schemas for API request and response validation.

Provides type-safe data validation for all API endpoints.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# ----- Chat Schemas -----


class HistoryPart(BaseModel):
    """A single part of a message in the chat history."""

    text: str


class HistoryItem(BaseModel):
    """
    A single message in the conversation history.
    
    Attributes:
        role: The role of the message sender ('user' or 'model').
        parts: List of message parts (typically containing text).
    """

    role: str = Field(..., description="Role: 'user' or 'model'")
    parts: List[HistoryPart]


class ChatRequest(BaseModel):
    """
    Request body for the chat endpoint.
    
    Attributes:
        question: The user's question to be answered.
        history: Optional conversation history for multi-turn chat.
    """

    question: str = Field(..., description="The question to ask")
    history: Optional[List[HistoryItem]] = Field(
        default_factory=list,
        description="Previous conversation history for context",
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

    loc: List[str] = Field(..., description="Location of the error")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """Response for validation errors (422)."""

    detail: List[ValidationErrorDetail]
