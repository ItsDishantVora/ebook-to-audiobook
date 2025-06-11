"""
File processing service for extracting text from PDF and EPUB files.
"""
import os
import re
from typing import Dict, List, Optional
import PyPDF2
import pdfplumber
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import structlog

from app.core.exceptions import FileProcessingError, TextExtractionError

logger = structlog.get_logger()

class FileProcessor:
    """Service for processing PDF and EPUB files."""
    
    def __init__(self):
        self.supported_formats = ["pdf", "epub"]
    
    async def extract_text_from_file(self, file_path: str, file_type: str) -> Dict[str, any]:
        """
        Extract text from a file based on its type.
        
        Args:
            file_path: Path to the file
            file_type: Type of file (pdf or epub)
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            if file_type.lower() == "pdf":
                return await self._extract_from_pdf(file_path)
            elif file_type.lower() == "epub":
                return await self._extract_from_epub(file_path)
            else:
                raise FileProcessingError(f"Unsupported file type: {file_type}")
        
        except Exception as e:
            logger.error("File processing failed", file_path=file_path, error=str(e))
            raise TextExtractionError(f"Failed to extract text from {file_type}: {str(e)}")
    
    async def _extract_from_pdf(self, file_path: str) -> Dict[str, any]:
        """Extract text from PDF file using multiple methods for better accuracy."""
        
        text_content = ""
        metadata = {}
        chapters = []
        
        try:
            # Method 1: Try pdfplumber first (better for complex layouts)
            try:
                with pdfplumber.open(file_path) as pdf:
                    metadata = {
                        "title": pdf.metadata.get("Title", ""),
                        "author": pdf.metadata.get("Author", ""),
                        "creator": pdf.metadata.get("Creator", ""),
                        "subject": pdf.metadata.get("Subject", ""),
                        "page_count": len(pdf.pages)
                    }
                    
                    for i, page in enumerate(pdf.pages):
                        page_text = page.extract_text() or ""
                        if page_text.strip():
                            text_content += f"\n\n--- Page {i+1} ---\n\n"
                            text_content += page_text
                            
                            # Try to detect chapter headings
                            potential_chapter = self._detect_chapter_heading(page_text)
                            if potential_chapter:
                                chapters.append({
                                    "title": potential_chapter,
                                    "page": i + 1,
                                    "start_position": len(text_content) - len(page_text)
                                })
                
                logger.info("PDF text extracted using pdfplumber", 
                           pages=len(pdf.pages), 
                           text_length=len(text_content))
                           
            except Exception as e:
                logger.warning("pdfplumber extraction failed, trying PyPDF2", error=str(e))
                
                # Method 2: Fallback to PyPDF2
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    
                    metadata = {
                        "title": pdf_reader.metadata.get("/Title", "") if pdf_reader.metadata else "",
                        "author": pdf_reader.metadata.get("/Author", "") if pdf_reader.metadata else "",
                        "page_count": len(pdf_reader.pages)
                    }
                    
                    for i, page in enumerate(pdf_reader.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text_content += f"\n\n--- Page {i+1} ---\n\n"
                                text_content += page_text
                        except Exception as page_error:
                            logger.warning("Failed to extract text from page", 
                                         page=i+1, error=str(page_error))
                            continue
            
            if not text_content.strip():
                raise TextExtractionError("No text could be extracted from PDF")
            
            # Clean up the extracted text
            text_content = self._clean_text(text_content)
            
            return {
                "raw_text": text_content,
                "metadata": metadata,
                "chapters": chapters,
                "word_count": len(text_content.split()),
                "character_count": len(text_content)
            }
            
        except Exception as e:
            logger.error("PDF processing failed", file_path=file_path, error=str(e))
            raise TextExtractionError(f"Failed to process PDF: {str(e)}")
    
    async def _extract_from_epub(self, file_path: str) -> Dict[str, any]:
        """Extract text from EPUB file."""
        
        try:
            book = epub.read_epub(file_path)
            
            # Extract metadata
            metadata = {
                "title": book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else "",
                "author": book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else "",
                "language": book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else "en",
                "description": book.get_metadata('DC', 'description')[0][0] if book.get_metadata('DC', 'description') else "",
            }
            
            text_content = ""
            chapters = []
            chapter_count = 0
            
            # Extract text from all items
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    chapter_count += 1
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    
                    # Extract chapter title
                    chapter_title = ""
                    title_tag = soup.find(['h1', 'h2', 'h3', 'title'])
                    if title_tag:
                        chapter_title = title_tag.get_text().strip()
                    
                    if not chapter_title:
                        chapter_title = f"Chapter {chapter_count}"
                    
                    # Extract chapter text
                    chapter_text = soup.get_text()
                    chapter_text = self._clean_text(chapter_text)
                    
                    if chapter_text.strip():
                        chapters.append({
                            "title": chapter_title,
                            "start_position": len(text_content),
                            "length": len(chapter_text),
                            "chapter_number": chapter_count
                        })
                        
                        text_content += f"\n\n=== {chapter_title} ===\n\n"
                        text_content += chapter_text
            
            if not text_content.strip():
                raise TextExtractionError("No text could be extracted from EPUB")
            
            # Final text cleanup
            text_content = self._clean_text(text_content)
            
            logger.info("EPUB text extracted successfully", 
                       chapters=len(chapters), 
                       text_length=len(text_content))
            
            return {
                "raw_text": text_content,
                "metadata": metadata,
                "chapters": chapters,
                "word_count": len(text_content.split()),
                "character_count": len(text_content)
            }
            
        except Exception as e:
            logger.error("EPUB processing failed", file_path=file_path, error=str(e))
            raise TextExtractionError(f"Failed to process EPUB: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Multiple newlines to double
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single
        text = re.sub(r'\t+', ' ', text)  # Tabs to spaces
        
        # Remove page numbers and headers/footers (common patterns)
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)  # Standalone page numbers
        text = re.sub(r'\n\s*Page \d+.*?\n', '\n', text)  # "Page X" patterns
        
        # Fix common OCR issues
        text = text.replace('�', '')  # Remove replacement characters
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Fix missing spaces
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text.strip()
    
    def _detect_chapter_heading(self, page_text: str) -> Optional[str]:
        """Try to detect chapter headings in PDF text."""
        
        lines = page_text.split('\n')
        
        for line in lines[:10]:  # Check first 10 lines of page
            line = line.strip()
            
            # Common chapter patterns
            chapter_patterns = [
                r'^Chapter\s+\d+',
                r'^CHAPTER\s+\d+',
                r'^\d+\.\s+[A-Z][a-z]+',
                r'^[IVX]+\.\s+[A-Z][a-z]+',
                r'^Part\s+\d+',
                r'^PART\s+\d+'
            ]
            
            for pattern in chapter_patterns:
                if re.match(pattern, line):
                    return line
        
        return None
    
    def validate_file(self, file_path: str, file_type: str) -> bool:
        """Validate if file can be processed."""
        
        if not os.path.exists(file_path):
            raise FileProcessingError(f"File not found: {file_path}")
        
        if file_type.lower() not in self.supported_formats:
            raise FileProcessingError(f"Unsupported file type: {file_type}")
        
        # Check file size (max 100MB as per config)
        file_size = os.path.getsize(file_path)
        max_size = 100 * 1024 * 1024  # 100MB
        
        if file_size > max_size:
            raise FileProcessingError(f"File too large: {file_size} bytes (max: {max_size} bytes)")
        
        return True 