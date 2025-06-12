"""Text processing module using Gemini AI for TTS optimization."""

import asyncio
import logging
import re
from typing import List, Dict, Optional
import google.generativeai as genai
from asyncio_throttle import Throttler

from config import settings

logger = logging.getLogger(__name__)

class TextProcessor:
    """Process and optimize text for TTS using Gemini AI."""
    
    def __init__(self):
        # Configure Gemini
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        
        # Rate limiting for cost optimization
        self.throttler = Throttler(rate_limit=15, period=60)  # 15 requests per minute for free tier
        
        # System prompt for TTS optimization
        self.system_prompt = """You are a text optimization expert for audiobook creation. Your task is to process text to make it perfect for text-to-speech conversion.

IMPORTANT INSTRUCTIONS:
1. Preserve the original meaning and content completely
2. Fix punctuation for natural speech flow
3. Break up extremely long sentences (>40 words) into shorter, more natural ones
4. Add appropriate pauses using "..." where natural speech would pause
5. Fix formatting artifacts (weird spacing, broken words, etc.)
6. Normalize numbers and abbreviations for speech (e.g., "Dr." → "Doctor", "3" → "three" in narrative context)
7. Remove or fix text that would sound awkward when spoken
8. Keep dialogue natural and conversational
9. Maintain paragraph breaks and structure
10. Add brief pauses "[pause]" between major sections if needed

DO NOT:
- Change the story, plot, or character names
- Add your own commentary or interpretations
- Remove important content
- Change the author's writing style significantly
- Add content that wasn't in the original

Return ONLY the optimized text, nothing else."""

    async def process_text(self, text: str, chunk_size: Optional[int] = None) -> str:
        """
        Process text using Gemini AI for TTS optimization.
        
        Args:
            text: Raw text to process
            chunk_size: Size of chunks to process (default from settings)
            
        Returns:
            Optimized text ready for TTS
        """
        if not text or not text.strip():
            return ""
        
        chunk_size = chunk_size or settings.max_chunk_size
        
        # Split text into chunks for processing
        chunks = self._split_text_into_chunks(text, chunk_size)
        
        logger.info(f"Processing {len(chunks)} text chunks with Gemini")
        
        # Process chunks concurrently with rate limiting
        processed_chunks = await self._process_chunks_async(chunks)
        
        # Combine processed chunks
        final_text = self._combine_chunks(processed_chunks)
        
        return final_text
    
    async def process_chapters(self, chapters: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Process multiple chapters with optimization.
        
        Args:
            chapters: List of chapter dictionaries with 'title' and 'text'
            
        Returns:
            List of processed chapters
        """
        processed_chapters = []
        
        for i, chapter in enumerate(chapters):
            logger.info(f"Processing chapter {i+1}/{len(chapters)}: {chapter.get('title', 'Untitled')}")
            
            processed_text = await self.process_text(chapter['text'])
            
            processed_chapters.append({
                'title': chapter['title'],
                'text': processed_text,
                'original_length': len(chapter['text']),
                'processed_length': len(processed_text)
            })
        
        return processed_chapters
    
    def _split_text_into_chunks(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks while preserving sentence boundaries."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        sentences = self._split_into_sentences(text)
        
        current_chunk = ""
        for sentence in sentences:
            # If adding this sentence would exceed chunk size, start a new chunk
            if current_chunk and len(current_chunk) + len(sentence) > chunk_size:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add the last chunk if it exists
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex."""
        # Simple sentence splitting - can be improved
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    async def _process_chunks_async(self, chunks: List[str]) -> List[str]:
        """Process chunks asynchronously with rate limiting."""
        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        
        async def process_single_chunk(chunk: str) -> str:
            async with semaphore:
                async with self.throttler:
                    return await self._process_single_chunk(chunk)
        
        # Process all chunks concurrently
        tasks = [process_single_chunk(chunk) for chunk in chunks]
        processed_chunks = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        result_chunks = []
        for i, result in enumerate(processed_chunks):
            if isinstance(result, Exception):
                logger.error(f"Error processing chunk {i}: {result}")
                # Fallback to basic processing
                result_chunks.append(self._basic_text_cleanup(chunks[i]))
            else:
                result_chunks.append(result)
        
        return result_chunks
    
    async def _process_single_chunk(self, chunk: str) -> str:
        """Process a single chunk with Gemini."""
        try:
            # Create the full prompt
            prompt = f"{self.system_prompt}\n\nText to optimize:\n{chunk}"
            
            # Generate response
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.gemini_temperature,
                    max_output_tokens=settings.gemini_max_tokens,
                )
            )
            
            if response.text:
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini, using basic cleanup")
                return self._basic_text_cleanup(chunk)
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            # Fallback to basic text cleanup
            return self._basic_text_cleanup(chunk)
    
    def _basic_text_cleanup(self, text: str) -> str:
        """Basic text cleanup as fallback when Gemini is unavailable."""
        if not text:
            return ""
        
        # Basic cleanup operations
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)  # Fix spacing after sentences
        text = re.sub(r'([a-z])([A-Z])', r'\1. \2', text)  # Add periods between sentences
        
        # Fix common issues
        text = text.replace(' ,', ',')
        text = text.replace(' .', '.')
        text = text.replace(' !', '!')
        text = text.replace(' ?', '?')
        text = text.replace('  ', ' ')
        
        # Add pauses for better TTS flow
        text = re.sub(r'([.!?])\s+([A-Z])', r'\1... \2', text)
        
        return text.strip()
    
    def _combine_chunks(self, chunks: List[str]) -> str:
        """Combine processed chunks back into a single text."""
        # Join chunks with appropriate spacing
        combined = ""
        for i, chunk in enumerate(chunks):
            if i == 0:
                combined = chunk
            else:
                # Add spacing between chunks
                if combined.endswith('.') or combined.endswith('!') or combined.endswith('?'):
                    combined += " " + chunk
                else:
                    combined += "... " + chunk
        
        return combined
    
    def add_speech_markers(self, text: str) -> str:
        """Add speech markers for better TTS pronunciation."""
        # Add pauses at chapter breaks
        text = re.sub(r'\n\s*\n+', '\n\n[pause]\n\n', text)
        
        # Add longer pauses at scene breaks (indicated by multiple line breaks)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n[pause]...[pause]\n\n', text)
        
        # Ensure proper pronunciation of common abbreviations
        abbreviations = {
            'Dr.': 'Doctor',
            'Mr.': 'Mister',
            'Mrs.': 'Missus',
            'Ms.': 'Miss',
            'Prof.': 'Professor',
            'St.': 'Saint',
            'vs.': 'versus',
            'etc.': 'etcetera',
            'i.e.': 'that is',
            'e.g.': 'for example',
        }
        
        for abbr, full in abbreviations.items():
            text = text.replace(abbr, full)
        
        return text
    
    def estimate_processing_cost(self, text: str) -> float:
        """Estimate the cost of processing text with Gemini."""
        # Gemini pricing (approximate)
        input_cost_per_1k = 0.00025  # $0.00025 per 1K characters
        output_cost_per_1k = 0.00075  # $0.00075 per 1K characters
        
        input_chars = len(text)
        # Estimate output will be similar length
        output_chars = input_chars * 1.1  # Slight increase due to optimization
        
        input_cost = (input_chars / 1000) * input_cost_per_1k
        output_cost = (output_chars / 1000) * output_cost_per_1k
        
        return input_cost + output_cost 