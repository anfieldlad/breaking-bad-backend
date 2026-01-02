"""
Domain model for documents stored in the vector database.

Represents the core business entity of the application.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Document:
    """
    Represents a document chunk stored in the vector database.
    
    Each document corresponds to a single page from a PDF file,
    containing the extracted text and its vector embedding.
    
    Attributes:
        text: The extracted text content from the PDF page.
        embedding: Vector embedding of the text for similarity search.
        filename: Original filename of the source PDF.
        chunk_id: Zero-based page/chunk index within the source file.
        id: Optional MongoDB ObjectId as string.
    """

    text: str
    embedding: List[float]
    filename: str
    chunk_id: int
    id: Optional[str] = field(default=None)

    def to_dict(self) -> dict:
        """Convert document to dictionary for MongoDB insertion."""
        return {
            "text": self.text,
            "embedding": self.embedding,
            "filename": self.filename,
            "chunk_id": self.chunk_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Document":
        """Create a Document instance from a MongoDB document."""
        return cls(
            text=data.get("text", ""),
            embedding=data.get("embedding", []),
            filename=data.get("filename", ""),
            chunk_id=data.get("chunk_id", 0),
            id=str(data.get("_id")) if data.get("_id") else None,
        )
