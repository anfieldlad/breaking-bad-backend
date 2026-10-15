"""
Abstract repository interface for document storage.

Defines the contract for document repositories, enabling dependency inversion
and allowing different storage implementations (MongoDB, PostgreSQL, etc.).
"""

from abc import ABC, abstractmethod
from typing import List

from app.models.document import Document


class DocumentRepositoryBase(ABC):
    """
    Abstract base class for document repositories.
    
    Defines the interface that all document repository implementations must follow.
    This enables the Dependency Inversion Principle - high-level modules (services)
    depend on this abstraction, not on concrete implementations.
    """

    @abstractmethod
    def insert_many(self, documents: List[Document]) -> int:
        """
        Insert multiple documents into the repository.
        
        Args:
            documents: List of Document objects to insert.
        
        Returns:
            Number of documents successfully inserted.
        
        Raises:
            DatabaseConnectionError: If the database connection fails.
        """
        pass

    @abstractmethod
    def replace_file(self, filename: str, documents: List[Document]) -> int:
        """
        Store `documents` as the complete set of chunks for `filename`.

        Any chunks previously stored for the same filename are removed, so
        re-ingesting a file updates it instead of duplicating it.

        Returns:
            Number of documents inserted.
        """

    @abstractmethod
    def vector_search(
        self,
        query_embedding: List[float],
        limit: int = 5,
    ) -> List[Document]:
        """
        Perform vector similarity search.
        
        Args:
            query_embedding: The query vector to search with.
            limit: Maximum number of results to return.
        
        Returns:
            List of Document objects sorted by similarity.
        
        Raises:
            VectorSearchError: If the vector search fails.
        """
        pass

    @abstractmethod
    def count_documents(self) -> int:
        """
        Get the total count of documents in the repository.
        
        Returns:
            Total number of documents.
        """
        pass

    @abstractmethod
    def delete_by_filename(self, filename: str) -> int:
        """
        Delete all documents from a specific file.

        Args:
            filename: The filename to delete documents for.

        Returns:
            Number of documents deleted.
        """
        pass

    @abstractmethod
    def delete_all(self) -> int:
        """
        Delete every document in the repository.

        Returns:
            Number of documents deleted.
        """
        pass

    def close(self) -> None:
        """Release any underlying resources (connections, clients)."""
