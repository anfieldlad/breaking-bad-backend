"""
Ingestion service for processing and storing PDF documents.

Orchestrates PDF processing, embedding generation, and document storage.
"""

from typing import List

from fastapi import UploadFile

from app.core.logging import get_logger
from app.models.document import Document
from app.repositories.base import DocumentRepositoryBase
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService

logger = get_logger(__name__)


class IngestionService:
    """
    Service for ingesting PDF documents into the vector database.
    
    Coordinates the full ingestion pipeline: validation, text extraction,
    embedding generation, and storage.
    
    Attributes:
        pdf_service: Service for PDF processing.
        embedding_service: Service for generating embeddings.
        repository: Document repository for storage.
    """

    def __init__(
        self,
        pdf_service: PDFService,
        embedding_service: EmbeddingService,
        repository: DocumentRepositoryBase,
    ):
        """
        Initialize the ingestion service.
        
        Args:
            pdf_service: Service for PDF processing.
            embedding_service: Service for generating embeddings.
            repository: Document repository for storage.
        """
        self.pdf_service = pdf_service
        self.embedding_service = embedding_service
        self.repository = repository
        logger.info("Ingestion service initialized")

    async def ingest_pdf(self, file: UploadFile) -> int:
        """
        Ingest a PDF file into the vector database.
        
        Performs the complete ingestion pipeline:
        1. Validate file type
        2. Extract text from PDF pages
        3. Generate embeddings for each page
        4. Store documents in the repository
        
        Args:
            file: The uploaded PDF file.
        
        Returns:
            Number of document chunks stored.
        
        Raises:
            InvalidFileTypeError: If the file is not a PDF.
            PDFProcessingError: If PDF processing fails.
            EmptyPDFError: If no text could be extracted.
            EmbeddingError: If embedding generation fails.
            DatabaseConnectionError: If storage fails.
        """
        filename = file.filename or "unknown.pdf"
        
        # Step 1: Validate file type
        self.pdf_service.validate_filename(filename)
        
        # Step 2: Read file content
        content = await file.read()
        
        # Step 3: Extract text from PDF
        extracted_pages = self.pdf_service.extract_text(content, filename)
        
        # Step 4: Generate embeddings and create documents
        documents: List[Document] = []
        
        for page in extracted_pages:
            embedding = self.embedding_service.embed_document(page.text)
            
            document = Document(
                text=page.text,
                embedding=embedding,
                filename=filename,
                chunk_id=page.page_number,
            )
            documents.append(document)
        
        # Step 5: Store documents
        stored_count = self.repository.insert_many(documents)
        
        logger.info(
            f"Ingestion complete for {filename}",
            extra={
                "filename": filename,
                "pages_extracted": len(extracted_pages),
                "documents_stored": stored_count,
            },
        )
        
        return stored_count
