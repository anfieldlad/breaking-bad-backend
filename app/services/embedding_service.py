"""
Embedding service for generating vector embeddings.

Encapsulates all embedding-related operations, providing a clean interface
for the rest of the application. The concrete backend (Google Gemini or any
OpenAI-compatible endpoint) is selected from configuration.
"""

from typing import List

from app.core.config import Settings
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger
from app.services.providers import get_embedding_provider

logger = get_logger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings.

    Provides methods for embedding documents (for storage) and queries
    (for retrieval), using the appropriate task types for each.

    Attributes:
        provider: The configured embedding backend.
        model: Name of the embedding model to use.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the embedding service.

        Args:
            settings: Application settings containing provider and model config.
        """
        self.provider = get_embedding_provider(settings)
        self.model = settings.embedding_model
        logger.info(
            f"Embedding service initialized "
            f"(provider={settings.embedding_provider}, model={self.model})"
        )

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
            embedding = self.provider.embed(text, task_type)

            logger.debug(
                f"Generated embedding",
                extra={"task_type": task_type, "dimension": len(embedding)},
            )
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {e}")
