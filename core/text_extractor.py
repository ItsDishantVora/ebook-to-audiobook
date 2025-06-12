"""Text extraction module for EPUB and PDF files."""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiofiles

# PDF processing
import PyPDF2
import pdfplumber

# EPUB processing
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from config import settings

logger = logging.getLogger(__name__)

class TextExtractor:
    """Extract text from various ebook formats."""
    
    def __init__(self):
        self.supported_formats = ['.epub', '.pdf', '.txt']
    
    async def extract_text(self, file_path: str) -> Dict[str, any]:
        """
        Extract text from an ebook file.
        
        Args:
            file_path: Path to the ebook file
            
        Returns:
            Dict containing:
            - text: Full text content
            - chapters: List of chapter texts
            - metadata: Book metadata
            - word_count: Approximate word count
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_extension = file_path.suffix.lower()
        
        if file_extension not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        logger.info(f"Extracting text from {file_path}")
        
        try:
            if file_extension == '.epub':
                return await self._extract_epub(file_path)
            elif file_extension == '.pdf':
                return await self._extract_pdf(file_path)
            elif file_extension == '.txt':
                return await self._extract_txt(file_path)
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            raise
    
    async def _extract_epub(self, file_path: Path) -> Dict[str, any]:
        """Extract text from EPUB file."""
        book = epub.read_epub(str(file_path))
        
        # Extract metadata
        metadata = {
            'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else 'Unknown',
            'author': book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else 'Unknown',
            'language': book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else 'en',
            'publisher': book.get_metadata('DC', 'publisher')[0][0] if book.get_metadata('DC', 'publisher') else 'Unknown',
        }
        
        chapters = []
        full_text = ""
        
        # Extract text from each chapter
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Parse HTML content
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Extract text
                chapter_text = soup.get_text()
                
                # Clean up text
                chapter_text = self._clean_text(chapter_text)
                
                if chapter_text.strip():  # Only add non-empty chapters
                    chapters.append({
                        'title': item.get_name(),
                        'text': chapter_text
                    })
                    full_text += chapter_text + "\n\n"
        
        word_count = len(full_text.split())
        
        return {
            'text': full_text.strip(),
            'chapters': chapters,
            'metadata': metadata,
            'word_count': word_count,
            'format': 'epub'
        }
    
    async def _extract_pdf(self, file_path: Path) -> Dict[str, any]:
        """Extract text from PDF file."""
        chapters = []
        full_text = ""
        
        # Try pdfplumber first (better text extraction)
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        page_text = self._clean_text(page_text)
                        chapters.append({
                            'title': f'Page {page_num + 1}',
                            'text': page_text
                        })
                        full_text += page_text + "\n\n"
        except Exception as e:
            logger.warning(f"pdfplumber failed, trying PyPDF2: {e}")
            
            # Fallback to PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        page_text = self._clean_text(page_text)
                        chapters.append({
                            'title': f'Page {page_num + 1}',
                            'text': page_text
                        })
                        full_text += page_text + "\n\n"
        
        # Basic metadata (PDFs don't always have rich metadata)
        metadata = {
            'title': file_path.stem,
            'author': 'Unknown',
            'language': 'en',
            'publisher': 'Unknown',
        }
        
        word_count = len(full_text.split())
        
        return {
            'text': full_text.strip(),
            'chapters': chapters,
            'metadata': metadata,
            'word_count': word_count,
            'format': 'pdf'
        }
    
    async def _extract_txt(self, file_path: Path) -> Dict[str, any]:
        """Extract text from TXT file."""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            full_text = await file.read()
        
        # For text files, we'll create artificial chapters based on length
        full_text = self._clean_text(full_text)
        chapters = self._split_into_chapters(full_text)
        
        metadata = {
            'title': file_path.stem,
            'author': 'Unknown',
            'language': 'en',
            'publisher': 'Unknown',
        }
        
        word_count = len(full_text.split())
        
        return {
            'text': full_text,
            'chapters': chapters,
            'metadata': metadata,
            'word_count': word_count,
            'format': 'txt'
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Normalize whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove excessive whitespace at beginning and end
        text = text.strip()
        
        # Handle common formatting issues
        text = text.replace('\u00a0', ' ')  # Non-breaking space
        text = text.replace('\ufeff', '')   # BOM character
        text = text.replace('â€™', "'")     # Smart quote
        text = text.replace('â€œ', '"')     # Smart quote
        text = text.replace('â€\x9d', '"')  # Smart quote
        text = text.replace('â€"', '—')     # Em dash
        
        return text
    
    def _split_into_chapters(self, text: str, max_words_per_chapter: int = 3000) -> List[Dict[str, str]]:
        """Split long text into manageable chapters."""
        words = text.split()
        chapters = []
        
        for i in range(0, len(words), max_words_per_chapter):
            chapter_words = words[i:i + max_words_per_chapter]
            chapter_text = ' '.join(chapter_words)
            
            chapters.append({
                'title': f'Chapter {len(chapters) + 1}',
                'text': chapter_text
            })
        
        return chapters
    
    async def validate_file(self, file_path: str) -> bool:
        """Validate if file can be processed."""
        try:
            file_path = Path(file_path)
            return (file_path.exists() and 
                   file_path.suffix.lower() in self.supported_formats and
                   file_path.stat().st_size > 0)
        except Exception:
            return False 