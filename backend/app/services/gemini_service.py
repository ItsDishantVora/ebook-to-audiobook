"""
Google Gemini AI service for text processing and enhancement.
"""
import asyncio
from typing import Dict, List, Optional
import google.generativeai as genai
import structlog

from app.core.config import settings
from app.core.exceptions import AIProcessingError

logger = structlog.get_logger()

class GeminiService:
    """Service for interacting with Google Gemini AI."""
    
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("Gemini API key not configured")
            self.model = None
        else:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                # Use Gemini 2.5 Flash Preview with adaptive thinking and cost efficiency
                self.model = genai.GenerativeModel('models/gemini-2.5-flash-preview-05-20')
                logger.info("Gemini AI service initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize Gemini AI", error=str(e))
                self.model = None
    
    async def enhance_text_for_audiobook(self, raw_text: str, book_metadata: Dict = None) -> str:
        """
        Enhance extracted text for better audiobook conversion.
        
        Args:
            raw_text: Raw extracted text from the book
            book_metadata: Optional metadata about the book
            
        Returns:
            Enhanced text optimized for TTS
        """
        if not self.model:
            logger.warning("Gemini model not available, returning original text")
            return raw_text
        
        try:
            # Split text into chunks for processing (Gemini has token limits)
            chunks = self._split_text_into_chunks(raw_text, max_chunk_size=8000)
            enhanced_chunks = []
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing text chunk {i+1}/{len(chunks)}")
                enhanced_chunk = await self._enhance_text_chunk(chunk, book_metadata)
                enhanced_chunks.append(enhanced_chunk)
                
                # Rate limiting: small delay between requests
                if i < len(chunks) - 1:
                    await asyncio.sleep(0.5)
            
            enhanced_text = "\n\n".join(enhanced_chunks)
            logger.info("Text enhancement completed", 
                       original_length=len(raw_text),
                       enhanced_length=len(enhanced_text))
            
            return enhanced_text
            
        except Exception as e:
            logger.error("Text enhancement failed", error=str(e))
            raise AIProcessingError(f"Failed to enhance text with Gemini: {str(e)}", "gemini")
    
    async def _enhance_text_chunk(self, text_chunk: str, book_metadata: Dict = None) -> str:
        """Enhance a single chunk of text."""
        
        title = book_metadata.get("title", "Unknown") if book_metadata else "Unknown"
        author = book_metadata.get("author", "Unknown") if book_metadata else "Unknown"
        
        prompt = f"""
You are an expert audiobook editor. Your task is to clean and optimize the following text for text-to-speech conversion.

Book Information:
- Title: {title}
- Author: {author}

Please perform the following optimizations:

1. **Fix formatting issues**: Remove any OCR errors, weird spacing, or broken sentences
2. **Improve readability**: Ensure proper sentence structure and flow
3. **Add pronunciation guides**: For difficult names, places, or technical terms, add phonetic hints in parentheses
4. **Fix dialogue**: Ensure proper quotation marks and speaker attribution
5. **Paragraph breaks**: Maintain proper paragraph structure for natural pauses
6. **Remove artifacts**: Clean up page numbers, headers, footers, or other non-content text
7. **Preserve meaning**: Do not change the actual content or meaning of the text

Guidelines:
- Keep the original voice and style of the author
- Do not summarize or shorten the content
- Focus on making it sound natural when read aloud
- For names/places that might be mispronounced, add phonetic guides like: "Hermione (her-MY-oh-nee)"

Text to enhance:

{text_chunk}

Please return the enhanced text optimized for audiobook narration:
"""
        
        try:
            response = await self._make_gemini_request(prompt)
            return response.strip()
        except Exception as e:
            logger.warning("Failed to enhance text chunk, returning original", error=str(e))
            return text_chunk
    
    async def detect_chapters(self, text: str) -> List[Dict]:
        """
        Use AI to detect and structure chapters in the text.
        
        Args:
            text: Full book text
            
        Returns:
            List of chapter information
        """
        if not self.model:
            logger.warning("Gemini model not available for chapter detection")
            return []
        
        try:
            prompt = f"""
Analyze the following book text and identify chapter breaks and titles.

Please return a JSON list of chapters with the following format:
[
  {{
    "chapter_number": 1,
    "title": "Chapter Title",
    "start_marker": "exact text that starts the chapter",
    "estimated_position": "approximate position in the text"
  }}
]

Guidelines:
- Look for clear chapter markers like "Chapter 1", "CHAPTER ONE", "Part I", etc.
- Include the actual chapter titles if present
- Be conservative - only identify clear chapter breaks
- If no clear chapters are found, return an empty list

Text to analyze (first 3000 characters):
{text[:3000]}

Please return only the JSON list, no other text:
"""
            
            response = await self._make_gemini_request(prompt)
            
            # Try to parse the JSON response
            import json
            try:
                chapters = json.loads(response)
                logger.info("Chapter detection completed", chapters_found=len(chapters))
                return chapters
            except json.JSONDecodeError:
                logger.warning("Failed to parse chapter detection response")
                return []
                
        except Exception as e:
            logger.error("Chapter detection failed", error=str(e))
            return []
    
    async def summarize_content(self, text: str, max_length: int = 500) -> str:
        """
        Generate a summary of the book content.
        
        Args:
            text: Book text to summarize
            max_length: Maximum length of summary
            
        Returns:
            Text summary
        """
        if not self.model:
            return "Summary not available (AI service not configured)"
        
        try:
            # Use a smaller chunk for summarization
            text_sample = text[:5000] if len(text) > 5000 else text
            
            prompt = f"""
Please provide a concise summary of this book content in approximately {max_length} characters.

The summary should:
- Capture the main themes and plot points
- Be engaging and informative
- Help readers understand what the book is about
- Be suitable for an audiobook description

Text to summarize:
{text_sample}

Summary:
"""
            
            response = await self._make_gemini_request(prompt)
            
            # Trim to requested length if needed
            if len(response) > max_length:
                response = response[:max_length-3] + "..."
            
            return response.strip()
            
        except Exception as e:
            logger.error("Content summarization failed", error=str(e))
            return "Summary not available"
    
    async def _make_gemini_request(self, prompt: str) -> str:
        """Make a request to Gemini API with error handling."""
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Lower temperature for more consistent output
                    max_output_tokens=2048,
                )
            )
            
            # Handle both simple and complex responses
            try:
                # Try simple text accessor first
                if hasattr(response, 'text') and response.text:
                    return response.text
            except Exception:
                # Fall back to parts accessor for complex responses
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if candidate.content and candidate.content.parts:
                        text_parts = []
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text_parts.append(part.text)
                        if text_parts:
                            return "".join(text_parts)
            
            raise AIProcessingError("No text content in Gemini response", "gemini")
                
        except Exception as e:
            logger.error("Gemini API request failed", error=str(e))
            raise AIProcessingError(f"Gemini API error: {str(e)}", "gemini")
    
    def _split_text_into_chunks(self, text: str, max_chunk_size: int = 8000) -> List[str]:
        """Split text into chunks that fit within token limits."""
        
        # Simple word-based splitting to stay within token limits
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            
            if current_size + word_size > max_chunk_size and current_chunk:
                # Finish current chunk
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size
        
        # Add the last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def is_available(self) -> bool:
        """Check if Gemini service is available."""
        return self.model is not None
    
    def list_available_models(self) -> List[str]:
        """List available Gemini models."""
        try:
            if not settings.GEMINI_API_KEY:
                return []
            
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            models = []
            for model in genai.list_models():
                if 'generateContent' in model.supported_generation_methods:
                    models.append(model.name)
            
            logger.info("Available Gemini models", models=models)
            return models
        except Exception as e:
            logger.error("Failed to list models", error=str(e))
            return [] 