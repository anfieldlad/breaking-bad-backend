"""
Chat service for RAG-based question answering.

Orchestrates retrieval and generation to provide context-aware answers
using the Breaking B.A.D. persona.
"""

import json
from typing import Generator, List, Optional

from google import genai
from google.genai import types

from app.core.config import Settings
from app.core.exceptions import ChatGenerationError
from app.core.logging import get_logger
from app.models.schemas import HistoryItem
from app.repositories.base import DocumentRepositoryBase
from app.services.embedding_service import EmbeddingService

logger = get_logger(__name__)

# System prompt for the Breaking B.A.D. persona
SYSTEM_PROMPT = """You are Breaking B.A.D. (Bot Answering Dialogue). 

Your primary source of truth is the provided 'Context'. 
- If the answer is in the context, use it to provide accurate, helpful responses.
- If the context doesn't contain the answer, you may answer using your general knowledge, 
  but maintain your persona and clarify if needed that the info isn't from the documents.
- Always be helpful and keep your persona consistent.
- Be concise but thorough in your responses."""


class ChatService:
    """
    Service for handling chat interactions with RAG capabilities.
    
    Combines vector search retrieval with LLM generation to provide
    context-aware responses based on ingested documents.
    
    Attributes:
        client: Google GenAI client instance.
        model: Name of the chat model to use.
        repository: Document repository for retrieval.
        embedding_service: Service for generating query embeddings.
        vector_search_limit: Maximum number of context documents to retrieve.
    """

    def __init__(
        self,
        settings: Settings,
        repository: DocumentRepositoryBase,
        embedding_service: EmbeddingService,
    ):
        """
        Initialize the chat service.
        
        Args:
            settings: Application settings.
            repository: Document repository for context retrieval.
            embedding_service: Service for generating embeddings.
        """
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.chat_model
        self.repository = repository
        self.embedding_service = embedding_service
        self.vector_search_limit = settings.vector_search_limit
        
        logger.info(f"Chat service initialized with model: {self.model}")

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
        
        Raises:
            ChatGenerationError: If response generation fails.
        """
        try:
            # Step 1: Retrieve context
            context, sources = self._retrieve_context(question)
            
            # Step 2: Send sources first
            yield f"data: {json.dumps({'sources': sources})}\n\n"
            
            # Step 3: Build conversation contents
            contents = self._build_contents(question, history)
            
            # Step 4: Generate streaming response
            yield from self._stream_response(contents, context)
            
        except Exception as e:
            logger.error(f"Chat generation failed: {e}")
            raise ChatGenerationError(f"Failed to generate response: {e}")

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
            context = "\n\n".join([doc.text for doc in documents])
            sources = list(set([doc.filename for doc in documents]))
            logger.debug(
                f"Retrieved {len(documents)} context documents",
                extra={"sources": sources},
            )
        else:
            context = "No relevant context found in the documents."
            sources = []
            logger.debug("No relevant context found")
        
        return context, sources

    def _build_contents(
        self,
        question: str,
        history: Optional[List[HistoryItem]] = None,
    ) -> List[types.Content]:
        """
        Build the conversation contents for the LLM.
        
        Args:
            question: The current question.
            history: Optional conversation history.
        
        Returns:
            List of Content objects for the LLM.
        """
        contents = []
        
        # Add history if available
        if history:
            for item in history:
                contents.append(
                    types.Content(
                        role=item.role,
                        parts=[types.Part(text=p.text) for p in item.parts],
                    )
                )
        
        # Add current question
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=question)],
            )
        )
        
        return contents

    def _stream_response(
        self,
        contents: List[types.Content],
        context: str,
    ) -> Generator[str, None, None]:
        """
        Stream the LLM response.
        
        Args:
            contents: The conversation contents.
            context: The retrieved context to include in the system prompt.
        
        Yields:
            SSE-formatted strings with thought and answer data.
        """
        system_instruction = f"{SYSTEM_PROMPT}\n\nContext:\n{context}"
        
        responses = self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
            ),
        )
        
        for response in responses:
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    data = {}
                    
                    if hasattr(part, 'thought') and part.thought:
                        data["thought"] = part.thought
                    if part.text:
                        data["answer"] = part.text
                    
                    if data:
                        yield f"data: {json.dumps(data)}\n\n"
