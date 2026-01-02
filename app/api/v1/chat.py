"""
Chat endpoint with streaming responses.

Provides RAG-based question answering with Server-Sent Events streaming.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.dependencies import APIKeyDep, ChatServiceDep
from app.core.exceptions import BreakingBadError
from app.core.logging import get_logger
from app.models.schemas import ChatRequest, ErrorResponse

logger = get_logger(__name__)

router = APIRouter(tags=["Chat"])


@router.post(
    "/chat",
    responses={
        200: {
            "description": "Streaming SSE response with sources, thoughts, and answers",
            "content": {"text/event-stream": {}},
        },
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        502: {"model": ErrorResponse, "description": "External service error"},
    },
    summary="Chat with Documents",
    description="Ask questions about ingested documents. Returns streaming SSE response with sources, reasoning, and answer.",
)
async def chat(
    request: ChatRequest,
    chat_service: ChatServiceDep,
    _api_key: APIKeyDep,
) -> StreamingResponse:
    """
    Ask a question and get a streaming response.
    
    The response is streamed as Server-Sent Events (SSE) with:
    - sources: List of document filenames used as context
    - thought: Model's reasoning process (if available)
    - answer: The generated response text
    
    Args:
        request: The chat request containing the question and optional history.
        chat_service: The injected chat service.
        _api_key: Verified API key (unused, but required for auth).
    
    Returns:
        StreamingResponse with SSE events.
    
    Raises:
        HTTPException: On chat generation errors.
    """
    try:
        return StreamingResponse(
            chat_service.generate_response_stream(
                question=request.question,
                history=request.history,
            ),
            media_type="text/event-stream",
        )
    except BreakingBadError as e:
        logger.error(f"Chat error: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.exception(f"Unexpected chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
