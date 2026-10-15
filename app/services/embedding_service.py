"""
Embedding service for generating vector embeddings.

Encapsulates all embedding-related operations, providing a clean interface
for the rest of the application. The concrete backend (Google Gemini or any
OpenAI-compatible endpoint) is selected from configuration.
"""

from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger
from app.services.providers import EmbeddingProvider

logger = get_logger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings.

    Provides methods for embedding documents (for storage) and queries
    (for retrieval), using the appropriate task types for each.

    Attributes:
        provider: The configured embedding backend.
    """

    def __init__(self, provider: EmbeddingProvider):
        """
        Initialize the embedding service.

        Args:
            provider: The embedding backend to use.
        """
        self.provider = provider

    def embed_document(self, text: str) -> list[float]:
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

    def embed_query(self, query: str) -> list[float]:
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

    def _generate_embedding(self, text: str, task_type: str) -> list[float]:
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
        except Exception as e:
            logger.exception("Failed to generate embedding (task_type=%s)", task_type)
            raise EmbeddingError() from e

        logger.debug("Generated embedding (task_type=%s, dim=%d)", task_type, len(embedding))
        return embedding
