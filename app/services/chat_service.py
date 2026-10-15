"""
Chat service for RAG-based question answering.

Orchestrates retrieval and generation to provide context-aware answers
using the Breaking B.A.D. persona.
"""

import json
from typing import Generator, List, Optional

from app.core.exceptions import ChatGenerationError
from app.core.logging import get_logger
from app.models.schemas import HistoryItem
from app.repositories.base import DocumentRepositoryBase
from app.services.embedding_service import EmbeddingService
from app.services.providers import ChatMessage, ChatProvider

logger = get_logger(__name__)

# System prompt for the Breaking B.A.D. persona
SYSTEM_PROMPT = """You are Breaking B.A.D. (Bot Answering Dialogue). 

Your primary source of truth is the provided 'Context'. 
- If the answer is in the context, use it to provide accurate, helpful responses.
- If the context doesn't contain the answer, you may answer using your general knowledge, 
  but maintain your persona and clarify if needed that the info isn't from the documents.
- Always be helpful and keep your persona consistent.
- Be concise but thorough in your responses."""


def _sse(payload: dict) -> str:
    """Format a payload as a single Server-Sent Events `data:` frame."""
    return f"data: {json.dumps(payload)}\n\n"


class ChatService:
    """
    Service for handling chat interactions with RAG capabilities.
    
    Combines vector search retrieval with LLM generation to provide
    context-aware responses based on ingested documents.

    Attributes:
        provider: The configured chat backend.
        repository: Document repository for retrieval.
        embedding_service: Service for generating query embeddings.
        vector_search_limit: Maximum number of context documents to retrieve.
    """

    def __init__(
        self,
        provider: ChatProvider,
        repository: DocumentRepositoryBase,
        embedding_service: EmbeddingService,
        vector_search_limit: int = 5,
    ):
        """
        Initialize the chat service.

        Args:
            provider: The chat backend to use.
            repository: Document repository for context retrieval.
            embedding_service: Service for generating embeddings.
            vector_search_limit: Maximum number of context documents.
        """
        self.provider = provider
        self.repository = repository
        self.embedding_service = embedding_service
        self.vector_search_limit = vector_search_limit

    def generate_response_stream(
        self,
        question: str,
        history: Optional[List[HistoryItem]] = None,
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response to a question.
        
        This method:
        1. Embeds the question
        2. Retrieves relevant context via vector search
        3. Streams the LLM response with context
        
        Args:
            question: The user's question.
            history: Optional conversation history.
        
        Yields:
            SSE-formatted strings containing sources, thoughts, and answers.
            If generation fails, a final ``{"error": ...}`` event is emitted
            instead of raising: the HTTP status (200) has already been sent
            once streaming starts, so failures must be reported in-band.
        """
        try:
            # Step 1: Retrieve context
            context, sources = self._retrieve_context(question)

            # Step 2: Send sources first
            yield _sse({"sources": sources})

            # Step 3: Build conversation messages
            messages = self._build_messages(question, history)

            # Step 4: Generate streaming response
            yield from self._stream_response(messages, context)

        except Exception:
            logger.exception("Chat generation failed")
            # Generic message only: provider/DB errors may contain internals.
            yield _sse({"error": ChatGenerationError.detail})

    def _retrieve_context(self, question: str) -> tuple[str, List[str]]:
        """
        Retrieve relevant context for the question.
        
        Args:
            question: The question to find context for.
        
        Returns:
            Tuple of (context_text, source_filenames).
        """
        query_embedding = self.embedding_service.embed_query(question)
        documents = self.repository.vector_search(
            query_embedding,
            limit=self.vector_search_limit,
        )
        
        if documents:
            context = "\n\n".join(doc.text for doc in documents)
            # Unique filenames, most relevant first.
            sources = list(dict.fromkeys(doc.filename for doc in documents))
            logger.debug("Retrieved %d context documents from %s", len(documents), sources)
        else:
            context = "No relevant context found in the documents."
            sources = []
            logger.debug("No relevant context found")
        
        return context, sources

    def _build_messages(
        self,
        question: str,
        history: Optional[List[HistoryItem]] = None,
    ) -> List[ChatMessage]:
        """
        Build the provider-neutral conversation messages for the LLM.

        Args:
            question: The current question.
            history: Optional conversation history.

        Returns:
            List of ChatMessage objects for the LLM.
        """
        messages: List[ChatMessage] = []

        # Add history if available
        if history:
            for item in history:
                text = "".join(p.text for p in item.parts)
                messages.append(ChatMessage(role=item.role, text=text))

        # Add current question
        messages.append(ChatMessage(role="user", text=question))

        return messages

    def _stream_response(
        self,
        messages: List[ChatMessage],
        context: str,
    ) -> Generator[str, None, None]:
        """
        Stream the LLM response.

        Args:
            messages: The conversation messages.
            context: The retrieved context to include in the system prompt.

        Yields:
            SSE-formatted strings with thought and answer data.
        """
        system_instruction = f"{SYSTEM_PROMPT}\n\nContext:\n{context}"

        for chunk in self.provider.stream(system_instruction, messages):
            data = {}

            if chunk.thought:
                data["thought"] = chunk.thought
            if chunk.answer:
                data["answer"] = chunk.answer

            if data:
                yield _sse(data)
