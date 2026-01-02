"""
PDF processing service for extracting text from PDF files.

Handles PDF parsing, text extraction, and validation with proper error handling.
"""

import io
from dataclasses import dataclass
from typing import List

from pypdf import PdfReader

from app.core.config import Settings
from app.core.exceptions import EmptyPDFError, InvalidFileTypeError, PDFProcessingError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedPage:
    """
    Represents a single extracted page from a PDF.
    
    Attributes:
        text: The extracted text content.
        page_number: Zero-based page index.
    """

    text: str
    page_number: int


class PDFService:
    """
    Service for processing PDF files.
    
    Handles validation, reading, and text extraction from PDF documents.
    
    Attributes:
        max_pages: Maximum number of pages to process per PDF.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the PDF service.
        
        Args:
            settings: Application settings containing processing limits.
        """
        self.max_pages = settings.max_pages_per_pdf
        logger.info(f"PDF service initialized with max pages: {self.max_pages}")

    def validate_filename(self, filename: str) -> None:
        """
        Validate that the file is a PDF based on filename.
        
        Args:
            filename: The name of the uploaded file.
        
        Raises:
            InvalidFileTypeError: If the file is not a PDF.
        """
        if not filename.lower().endswith(".pdf"):
            logger.warning(f"Invalid file type uploaded: {filename}")
            raise InvalidFileTypeError(f"File '{filename}' is not a PDF")

    def extract_text(self, file_content: bytes, filename: str) -> List[ExtractedPage]:
        """
        Extract text from a PDF file.
        
        Args:
            file_content: The raw bytes of the PDF file.
            filename: The original filename (for logging).
        
        Returns:
            List of ExtractedPage objects containing text from each page.
        
        Raises:
            PDFProcessingError: If PDF parsing fails.
            EmptyPDFError: If no text could be extracted.
        """
        try:
            pdf_reader = PdfReader(io.BytesIO(file_content))
            num_pages = min(len(pdf_reader.pages), self.max_pages)
            
            logger.info(
                f"Processing PDF: {filename}",
                extra={
                    "total_pages": len(pdf_reader.pages),
                    "processing_pages": num_pages,
                },
            )

            extracted_pages: List[ExtractedPage] = []

            for i in range(num_pages):
                page = pdf_reader.pages[i]
                text = page.extract_text()

                if text and text.strip():
                    extracted_pages.append(
                        ExtractedPage(text=text.strip(), page_number=i)
                    )

            if not extracted_pages:
                logger.warning(f"No extractable text in PDF: {filename}")
                raise EmptyPDFError(f"PDF '{filename}' contains no extractable text")

            logger.info(
                f"Extracted text from {len(extracted_pages)} pages",
                extra={"filename": filename, "pages_with_text": len(extracted_pages)},
            )
            return extracted_pages

        except EmptyPDFError:
            raise
        except Exception as e:
            logger.error(f"Failed to process PDF '{filename}': {e}")
            raise PDFProcessingError(f"Failed to process PDF: {e}")
