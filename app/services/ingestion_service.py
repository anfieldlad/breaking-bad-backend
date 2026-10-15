"""
Ingestion service for processing and storing PDF documents.

Orchestrates PDF processing, embedding generation, and document storage.
"""

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

    def ingest_pdf(self, content: bytes, filename: str) -> int:
        """
        Ingest a PDF file into the vector database.

        Performs the complete ingestion pipeline:
        1. Validate file type (name and content)
        2. Extract text from PDF pages
        3. Generate embeddings for each page
        4. Store documents, replacing any previous version of the file

        This method does blocking I/O; call it from a worker thread when
        serving async requests.

        Args:
            content: The raw bytes of the uploaded file.
            filename: The uploaded file's name.

        Returns:
            Number of document chunks stored.

        Raises:
            InvalidFileTypeError: If the file is not a PDF.
            PDFProcessingError: If PDF processing fails.
            EmptyPDFError: If no text could be extracted.
            EmbeddingError: If embedding generation fails.
            DatabaseConnectionError: If storage fails.
        """
        self.pdf_service.validate_filename(filename)
        self.pdf_service.validate_content(content, filename)

        extracted_pages = self.pdf_service.extract_text(content, filename)

        documents: list[Document] = [
            Document(
                text=page.text,
                embedding=self.embedding_service.embed_document(page.text),
                filename=filename,
                chunk_id=page.page_number,
            )
            for page in extracted_pages
        ]

        stored_count = self.repository.replace_file(filename, documents)

        logger.info(
            "Ingestion complete for %s (%d pages extracted, %d chunks stored)",
            filename,
            len(extracted_pages),
            stored_count,
        )
        return stored_count
