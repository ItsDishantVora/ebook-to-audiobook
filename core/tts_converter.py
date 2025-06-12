"""Text-to-Speech conversion module with multiple engine support."""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Union
import aiofiles

# TTS engines
import edge_tts
from gtts import gTTS
import pyttsx3

from config import settings

logger = logging.getLogger(__name__)

class TTSConverter:
    """Convert text to speech using various TTS engines."""
    
    def __init__(self, engine: str = None, voice: str = None):
        self.engine = engine or settings.tts_engine
        self.voice = voice or settings.default_voice
        self.supported_engines = ['edge-tts', 'gtts', 'pyttsx3']
        
        if self.engine not in self.supported_engines:
            raise ValueError(f"Unsupported TTS engine: {self.engine}")
        
        # Initialize pyttsx3 engine if needed
        self.pyttsx3_engine = None
        if self.engine == 'pyttsx3':
            self._init_pyttsx3()
    
    def _init_pyttsx3(self):
        """Initialize pyttsx3 engine."""
        try:
            self.pyttsx3_engine = pyttsx3.init()
            self.pyttsx3_engine.setProperty('rate', int(settings.speech_rate * 150))
            voices = self.pyttsx3_engine.getProperty('voices')
            if voices:
                self.pyttsx3_engine.setProperty('voice', voices[0].id)
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3: {e}")
            raise
    
    async def convert_text_to_audio(self, text: str, output_path: str) -> bool:
        """
        Convert text to audio file.
        
        Args:
            text: Text to convert
            output_path: Path to save the audio file
            
        Returns:
            True if successful, False otherwise
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS conversion")
            return False
        
        try:
            if self.engine == 'edge-tts':
                return await self._convert_with_edge_tts(text, output_path)
            elif self.engine == 'gtts':
                return await self._convert_with_gtts(text, output_path)
            elif self.engine == 'pyttsx3':
                return await self._convert_with_pyttsx3(text, output_path)
        except Exception as e:
            logger.error(f"TTS conversion failed: {e}")
            return False
    
    async def convert_chapters_to_audio(self, chapters: List[Dict[str, str]], 
                                      output_dir: str) -> List[str]:
        """
        Convert multiple chapters to audio files.
        
        Args:
            chapters: List of chapter dictionaries with 'title' and 'text'
            output_dir: Directory to save audio files
            
        Returns:
            List of audio file paths
        """
        os.makedirs(output_dir, exist_ok=True)
        audio_files = []
        
        # Convert chapters concurrently
        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        
        async def convert_single_chapter(chapter: Dict[str, str], index: int) -> Optional[str]:
            async with semaphore:
                chapter_title = chapter.get('title', f'Chapter {index + 1}')
                safe_title = self._sanitize_filename(chapter_title)
                output_path = os.path.join(output_dir, f"{index:03d}_{safe_title}.mp3")
                
                logger.info(f"Converting chapter: {chapter_title}")
                
                # Process text for TTS
                processed_text = self._prepare_text_for_tts(chapter['text'])
                
                success = await self.convert_text_to_audio(processed_text, output_path)
                
                if success:
                    return output_path
                else:
                    logger.error(f"Failed to convert chapter: {chapter_title}")
                    return None
        
        # Convert all chapters
        tasks = [convert_single_chapter(chapter, i) for i, chapter in enumerate(chapters)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful conversions
        for result in results:
            if isinstance(result, str) and result:
                audio_files.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Chapter conversion error: {result}")
        
        return sorted(audio_files)  # Sort to maintain order
    
    async def _convert_with_edge_tts(self, text: str, output_path: str) -> bool:
        """Convert text using Edge TTS."""
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(output_path)
            return True
        except Exception as e:
            logger.error(f"Edge TTS conversion failed: {e}")
            return False
    
    async def _convert_with_gtts(self, text: str, output_path: str) -> bool:
        """Convert text using Google TTS."""
        try:
            # Extract language from voice (e.g., 'en-US-AriaNeural' -> 'en')
            language = self.voice.split('-')[0] if '-' in self.voice else 'en'
            
            # Create gTTS object
            tts = gTTS(text=text, lang=language, slow=False)
            
            # Save to file
            tts.save(output_path)
            return True
        except Exception as e:
            logger.error(f"Google TTS conversion failed: {e}")
            return False
    
    async def _convert_with_pyttsx3(self, text: str, output_path: str) -> bool:
        """Convert text using pyttsx3."""
        try:
            if not self.pyttsx3_engine:
                self._init_pyttsx3()
            
            # pyttsx3 saves to file directly
            self.pyttsx3_engine.save_to_file(text, output_path)
            self.pyttsx3_engine.runAndWait()
            
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"pyttsx3 conversion failed: {e}")
            return False
    
    def _prepare_text_for_tts(self, text: str) -> str:
        """Prepare text for TTS conversion."""
        if not text:
            return ""
        
        # Handle pause markers
        text = text.replace('[pause]', '... ')
        text = text.replace('###', '... ')
        
        # Normalize whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Ensure proper sentence ending
        if not text.endswith(('.', '!', '?')):
            text += '.'
        
        return text
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file system usage."""
        import re
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        filename = filename.strip('._')
        
        # Limit length
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename or 'untitled'
    
    @staticmethod
    def get_available_voices() -> Dict[str, List[str]]:
        """Get available voices for each TTS engine."""
        voices = {
            'edge-tts': [
                'en-US-AriaNeural',
                'en-US-JennyNeural',
                'en-US-GuyNeural',
                'en-US-JasonNeural',
                'en-US-MichelleNeural',
                'en-GB-SoniaNeural',
                'en-GB-RyanNeural',
                'en-AU-NatashaNeural',
                'en-AU-WilliamNeural',
                'en-CA-ClaraNeural',
                'en-CA-LiamNeural',
            ],
            'gtts': [
                'en',  # English
                'es',  # Spanish
                'fr',  # French
                'de',  # German
                'it',  # Italian
                'pt',  # Portuguese
                'ru',  # Russian
                'ja',  # Japanese
                'ko',  # Korean
                'zh',  # Chinese
            ],
            'pyttsx3': ['default']  # System voices
        }
        
        return voices
    
    async def get_voice_sample(self, voice: str, sample_text: str = "Hello, this is a voice sample.") -> str:
        """Generate a voice sample for testing."""
        temp_path = os.path.join(settings.temp_dir, f"voice_sample_{voice.replace('-', '_')}.mp3")
        
        original_voice = self.voice
        self.voice = voice
        
        try:
            success = await self.convert_text_to_audio(sample_text, temp_path)
            if success:
                return temp_path
            else:
                return None
        finally:
            self.voice = original_voice
    
    def estimate_audio_duration(self, text: str, words_per_minute: int = 150) -> float:
        """Estimate audio duration in seconds."""
        word_count = len(text.split())
        duration_minutes = word_count / words_per_minute
        return duration_minutes * 60
    
    def get_engine_info(self) -> Dict[str, any]:
        """Get information about the current TTS engine."""
        return {
            'engine': self.engine,
            'voice': self.voice,
            'supported_formats': ['mp3', 'wav'],
            'quality': 'high' if self.engine == 'edge-tts' else 'medium',
            'cost': 'free',
            'speed': 'fast' if self.engine == 'edge-tts' else 'medium'
        } 