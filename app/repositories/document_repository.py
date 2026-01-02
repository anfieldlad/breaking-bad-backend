"""
MongoDB implementation of the document repository.

Provides concrete implementation for document storage using MongoDB Atlas
with vector search capabilities.
"""

from typing import List, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.core.config import Settings
from app.core.exceptions import DatabaseConnectionError, VectorSearchError
from app.core.logging import get_logger
from app.models.document import Document
from app.repositories.base import DocumentRepositoryBase

logger = get_logger(__name__)


class MongoDocumentRepository(DocumentRepositoryBase):
    """
    MongoDB implementation of the document repository.
    
    Uses MongoDB Atlas Vector Search for similarity queries.
    
    Attributes:
        client: MongoDB client instance.
        db: Database instance.
        collection: Collection for document storage.
        settings: Application settings.
    """

    def __init__(
        self,
        settings: Settings,
        client: Optional[MongoClient] = None,
    ):
        """
        Initialize the MongoDB repository.
        
        Args:
            settings: Application settings containing connection details.
            client: Optional pre-configured MongoDB client (for testing).
        """
        self.settings = settings
        
        try:
            self.client: MongoClient = client or MongoClient(settings.mongo_uri)
            self.db: Database = self.client[settings.db_name]
            self.collection: Collection = self.db[settings.collection_name]
            logger.info(
                "MongoDB repository initialized",
                extra={
                    "database": settings.db_name,
                    "collection": settings.collection_name,
                },
            )
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise DatabaseConnectionError(f"Failed to connect to MongoDB: {e}")

    def insert_many(self, documents: List[Document]) -> int:
        """Insert multiple documents into MongoDB."""
        if not documents:
            logger.warning("Attempted to insert empty document list")
            return 0

        try:
            docs_to_insert = [doc.to_dict() for doc in documents]
            result = self.collection.insert_many(docs_to_insert)
            inserted_count = len(result.inserted_ids)
            
            logger.info(
                f"Inserted {inserted_count} documents",
                extra={"inserted_count": inserted_count},
            )
            return inserted_count
        except Exception as e:
            logger.error(f"Failed to insert documents: {e}")
            raise DatabaseConnectionError(f"Failed to insert documents: {e}")

    def vector_search(
        self,
        query_embedding: List[float],
        limit: int = 5,
    ) -> List[Document]:
        """
        Perform vector similarity search using MongoDB Atlas Vector Search.
        
        Requires a vector search index named as configured in settings.
        """
        try:
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.settings.vector_index_name,
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": self.settings.vector_search_candidates,
                        "limit": limit,
                    }
                }
            ]

            results = list(self.collection.aggregate(pipeline))
            documents = [Document.from_dict(doc) for doc in results]
            
            logger.debug(
                f"Vector search returned {len(documents)} results",
                extra={"result_count": len(documents), "limit": limit},
            )
            return documents
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise VectorSearchError(f"Vector search failed: {e}")

    def count_documents(self) -> int:
        """Get total document count."""
        try:
            return self.collection.count_documents({})
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            raise DatabaseConnectionError(f"Failed to count documents: {e}")

    def delete_by_filename(self, filename: str) -> int:
        """Delete all documents from a specific file."""
        try:
            result = self.collection.delete_many({"filename": filename})
            deleted_count = result.deleted_count
            
            logger.info(
                f"Deleted {deleted_count} documents for file: {filename}",
                extra={"filename": filename, "deleted_count": deleted_count},
            )
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            raise DatabaseConnectionError(f"Failed to delete documents: {e}")

    def close(self) -> None:
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
