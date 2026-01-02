"""
Embedding service for generating vector embeddings using Google Gemini.

Encapsulates all embedding-related operations, providing a clean interface
for the rest of the application.
"""

from typing import List

from google import genai
from google.genai import types

from app.core.config import Settings
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using Google Gemini API.
    
    Provides methods for embedding documents (for storage) and queries
    (for retrieval), using the appropriate task types for each.
    
    Attributes:
        client: Google GenAI client instance.
        model: Name of the embedding model to use.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the embedding service.
        
        Args:
            settings: Application settings containing API key and model config.
        """
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.embedding_model
        logger.info(f"Embedding service initialized with model: {self.model}")

    def embed_document(self, text: str) -> List[float]:
        """
        Generate embedding for a document chunk.
        
        Uses RETRIEVAL_DOCUMENT task type optimized for document storage.
        
        Args:
            text: The document text to embed.
        
        Returns:
            List of float values representing the embedding vector.
        
        Raises:
            EmbeddingError: If embedding generation fails.
        """
        return self._generate_embedding(text, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Uses RETRIEVAL_QUERY task type optimized for search queries.
        
        Args:
            query: The search query to embed.
        
        Returns:
            List of float values representing the embedding vector.
        
        Raises:
            EmbeddingError: If embedding generation fails.
        """
        return self._generate_embedding(query, task_type="RETRIEVAL_QUERY")

    def _generate_embedding(self, text: str, task_type: str) -> List[float]:
        """
        Internal method to generate embeddings with specified task type.
        
        Args:
            text: The text to embed.
            task_type: The embedding task type (RETRIEVAL_DOCUMENT or RETRIEVAL_QUERY).
        
        Returns:
            List of float values representing the embedding vector.
        
        Raises:
            EmbeddingError: If embedding generation fails.
        """
        try:
            response = self.client.models.embed_content(
                model=self.model,
                contents=text,
                config=types.EmbedContentConfig(task_type=task_type),
            )
            embedding = response.embeddings[0].values
            
            logger.debug(
                f"Generated embedding",
                extra={"task_type": task_type, "dimension": len(embedding)},
            )
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {e}")
