"""
MongoDB implementation of the document repository.

Provides concrete implementation for document storage using MongoDB Atlas
with vector search capabilities.
"""

import uuid
from typing import List, Optional

from pymongo import MongoClient
from pymongo.collection import Collection

from app.core.config import Settings
from app.core.exceptions import DatabaseConnectionError, VectorSearchError
from app.core.logging import get_logger
from app.models.document import Document
from app.repositories.base import DocumentRepositoryBase

logger = get_logger(__name__)


class MongoDocumentRepository(DocumentRepositoryBase):
    """
    MongoDB implementation of the document repository.

    Uses MongoDB Atlas Vector Search for similarity queries. Driver errors
    are logged with full details and re-raised as application errors with
    generic, client-safe messages.
    """

    def __init__(
        self,
        settings: Settings,
        client: Optional[MongoClient] = None,
    ):
        """
        Initialize the MongoDB repository.

        The client connects lazily, so no network I/O happens here.

        Args:
            settings: Application settings containing connection details.
            client: Optional pre-configured MongoDB client (for testing).
        """
        self.settings = settings
        self.client: MongoClient = client or MongoClient(
            settings.mongo_uri, serverSelectionTimeoutMS=settings.mongo_timeout_ms
        )
        self.collection: Collection = self.client[settings.db_name][settings.collection_name]
        logger.info(
            "MongoDB repository initialized (database=%s, collection=%s)",
            settings.db_name,
            settings.collection_name,
        )

    def insert_many(self, documents: List[Document]) -> int:
        """Insert multiple documents into MongoDB."""
        if not documents:
            logger.warning("Attempted to insert empty document list")
            return 0

        try:
            result = self.collection.insert_many([doc.to_dict() for doc in documents])
        except Exception as e:
            logger.exception("Failed to insert documents")
            raise DatabaseConnectionError() from e

        logger.info("Inserted %d documents", len(result.inserted_ids))
        return len(result.inserted_ids)

    def replace_file(self, filename: str, documents: List[Document]) -> int:
        """
        Replace all chunks of `filename` with `documents`.

        New chunks are inserted first (tagged with a fresh ingest id) and the
        previous version is deleted afterwards, so a failed insert never
        loses the existing copy of the file.
        """
        ingest_id = uuid.uuid4().hex
        try:
            result = self.collection.insert_many(
                [{**doc.to_dict(), "ingest_id": ingest_id} for doc in documents]
            )
            removed = self.collection.delete_many(
                {"filename": filename, "ingest_id": {"$ne": ingest_id}}
            ).deleted_count
        except Exception as e:
            logger.exception("Failed to store documents for %s", filename)
            raise DatabaseConnectionError() from e

        logger.info(
            "Stored %d chunks for %s (replaced %d previous chunks)",
            len(result.inserted_ids),
            filename,
            removed,
        )
        return len(result.inserted_ids)

    def vector_search(
        self,
        query_embedding: List[float],
        limit: int = 5,
    ) -> List[Document]:
        """
        Perform vector similarity search using MongoDB Atlas Vector Search.

        Requires a vector search index named as configured in settings.
        Embeddings are projected out of the results (they are large and
        unused by callers); the similarity score is included instead.
        """
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.settings.vector_index_name,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": self.settings.vector_search_candidates,
                    "limit": limit,
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "text": 1,
                    "filename": 1,
                    "chunk_id": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        try:
            results = list(self.collection.aggregate(pipeline))
        except Exception as e:
            logger.exception("Vector search failed")
            raise VectorSearchError() from e

        logger.debug("Vector search returned %d results (limit=%d)", len(results), limit)
        return [Document.from_dict(doc) for doc in results]

    def count_documents(self) -> int:
        """Get total document count."""
        try:
            return self.collection.count_documents({})
        except Exception as e:
            logger.exception("Failed to count documents")
            raise DatabaseConnectionError() from e

    def delete_by_filename(self, filename: str) -> int:
        """Delete all documents from a specific file."""
        try:
            deleted_count = self.collection.delete_many({"filename": filename}).deleted_count
        except Exception as e:
            logger.exception("Failed to delete documents for %s", filename)
            raise DatabaseConnectionError() from e

        logger.info("Deleted %d documents for file %s", deleted_count, filename)
        return deleted_count

    def delete_all(self) -> int:
        """Delete every document in the collection."""
        try:
            deleted_count = self.collection.delete_many({}).deleted_count
        except Exception as e:
            logger.exception("Failed to delete all documents")
            raise DatabaseConnectionError() from e

        logger.info("Deleted all %d documents", deleted_count)
        return deleted_count

    def ping(self) -> bool:
        """Return True if the database answers a ping."""
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            logger.warning("MongoDB ping failed", exc_info=True)
            return False

    def close(self) -> None:
        """Close the MongoDB connection."""
        self.client.close()
        logger.info("MongoDB connection closed")
