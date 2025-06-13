"""Text-to-Speech conversion module with multiple engine support and caching."""

import asyncio
import logging
import os
import tempfile
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional, Union
import aiofiles
import diskcache as dc
import soundfile as sf

# TTS engines
import edge_tts
from gtts import gTTS
import pyttsx3

# Coqui TTS
try:
    from TTS.api import TTS
    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False
    logging.warning("Coqui TTS not available. Install with: pip install TTS")

from config import settings

logger = logging.getLogger(__name__)

class TTSConverter:
    """Convert text to speech using various TTS engines with caching."""
    
    def __init__(self, engine: str = None, voice: str = None):
        self.engine = engine or settings.tts_engine
        self.voice = voice or settings.default_voice
        self.supported_engines = ['coqui-xtts', 'edge-tts', 'gtts', 'pyttsx3']
        
        # Initialize cache
        self.cache = dc.Cache(os.path.join(settings.temp_dir, 'tts_cache'))
        self.cache_enabled = True
        
        if self.engine not in self.supported_engines:
            logger.warning(f"Engine {self.engine} not supported. Falling back to edge-tts")
            self.engine = 'edge-tts'
        
        # Initialize engines
        self.coqui_tts = None
        self.pyttsx3_engine = None
        
        self._init_engines()
    
    def _init_engines(self):
        """Initialize TTS engines."""
        if self.engine == 'coqui-xtts' and COQUI_AVAILABLE:
            self._init_coqui_tts()
        elif self.engine == 'pyttsx3':
            self._init_pyttsx3()
    
    def _init_coqui_tts(self):
        """Initialize Coqui TTS with English-optimized models."""
        try:
            # Use the best English model for high quality
            model_name = "tts_models/en/ljspeech/tacotron2-DDC"  # High quality English
            # Alternative: "tts_models/en/vctk/vits" for multi-speaker
            
            logger.info(f"Loading Coqui TTS model: {model_name}")
            self.coqui_tts = TTS(model_name=model_name, progress_bar=False)
            
            # Enable GPU if available
            import torch
            if torch.cuda.is_available():
                self.coqui_tts = self.coqui_tts.to("cuda")
                logger.info("Coqui TTS using GPU acceleration")
            else:
                logger.info("Coqui TTS using CPU")
                
        except Exception as e:
            logger.error(f"Failed to initialize Coqui TTS: {e}")
            logger.info("Falling back to Edge TTS")
            self.engine = 'edge-tts'
            self.coqui_tts = None
    
    def _init_pyttsx3(self):
        """Initialize pyttsx3 engine."""
        try:
            self.pyttsx3_engine = pyttsx3.init()
            self.pyttsx3_engine.setProperty('rate', int(settings.speech_rate * 150))
            voices = self.pyttsx3_engine.getProperty('voices')
            if voices:
                # Find best English voice
                english_voices = [v for v in voices if 'en' in v.id.lower() or 'english' in v.name.lower()]
                if english_voices:
                    self.pyttsx3_engine.setProperty('voice', english_voices[0].id)
                else:
                    self.pyttsx3_engine.setProperty('voice', voices[0].id)
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3: {e}")
            raise
    
    def _get_cache_key(self, text: str, engine: str, voice: str) -> str:
        """Generate cache key for text and settings."""
        content = f"{text}_{engine}_{voice}_{settings.speech_rate}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def convert_text_to_audio(self, text: str, output_path: str) -> bool:
        """
        Convert text to audio file with caching.
        
        Args:
            text: Text to convert
            output_path: Path to save the audio file
            
        Returns:
            True if successful, False otherwise
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS conversion")
            return False
        
        # Check cache first
        cache_key = self._get_cache_key(text, self.engine, self.voice)
        
        if self.cache_enabled and cache_key in self.cache:
            logger.info(f"Using cached audio for text: {text[:50]}...")
            try:
                cached_audio = self.cache[cache_key]
                async with aiofiles.open(output_path, 'wb') as f:
                    await f.write(cached_audio)
                return True
            except Exception as e:
                logger.warning(f"Failed to use cached audio: {e}")
        
        try:
            # Convert based on engine
            success = False
            if self.engine == 'coqui-xtts':
                success = await self._convert_with_coqui_tts(text, output_path)
            elif self.engine == 'edge-tts':
                success = await self._convert_with_edge_tts(text, output_path)
            elif self.engine == 'gtts':
                success = await self._convert_with_gtts(text, output_path)
            elif self.engine == 'pyttsx3':
                success = await self._convert_with_pyttsx3(text, output_path)
            
            # Cache the result if successful
            if success and self.cache_enabled:
                try:
                    async with aiofiles.open(output_path, 'rb') as f:
                        audio_data = await f.read()
                        self.cache[cache_key] = audio_data
                        logger.debug(f"Cached audio for key: {cache_key}")
                except Exception as e:
                    logger.warning(f"Failed to cache audio: {e}")
            
            return success
            
        except Exception as e:
            logger.error(f"TTS conversion failed: {e}")
            return False
    
    async def convert_chapters_to_audio(self, chapters: List[Dict[str, str]], 
                                      output_dir: str) -> List[str]:
        """
        Convert multiple chapters to audio files with optimized concurrency.
        """
        os.makedirs(output_dir, exist_ok=True)
        audio_files = []
        
        # Adjust concurrency based on engine
        max_concurrent = 2 if self.engine == 'coqui-xtts' else settings.max_concurrent_requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def convert_single_chapter(chapter: Dict[str, str], index: int) -> Optional[str]:
            async with semaphore:
                chapter_title = chapter.get('title', f'Chapter {index + 1}')
                safe_title = self._sanitize_filename(chapter_title)
                output_path = os.path.join(output_dir, f"{index:03d}_{safe_title}.mp3")
                
                logger.info(f"Converting chapter: {chapter_title}")
                
                # Process text for TTS with English optimizations
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
        
        return sorted(audio_files)
    
    async def _convert_with_coqui_tts(self, text: str, output_path: str) -> bool:
        """Convert text using Coqui TTS - Highest Quality."""
        try:
            if not self.coqui_tts:
                raise Exception("Coqui TTS not initialized")
            
            # Coqui TTS runs synchronously, so run in thread pool
            import asyncio
            loop = asyncio.get_event_loop()
            
            def sync_convert():
                self.coqui_tts.tts_to_file(
                    text=text,
                    file_path=output_path
                )
            
            await loop.run_in_executor(None, sync_convert)
            return os.path.exists(output_path)
            
        except Exception as e:
            logger.error(f"Coqui TTS conversion failed: {e}")
            return False
    
    async def _convert_with_edge_tts(self, text: str, output_path: str) -> bool:
        """Convert text using Edge TTS."""
        try:
            # Use higher quality English voices
            if self.voice == "en-US-AriaNeural":
                voice = "en-US-AriaNeural"  # Very natural
            elif "en" in self.voice.lower():
                voice = self.voice
            else:
                voice = "en-US-AriaNeural"  # Default to best English voice
            
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return True
        except Exception as e:
            logger.error(f"Edge TTS conversion failed: {e}")
            return False
    
    async def _convert_with_gtts(self, text: str, output_path: str) -> bool:
        """Convert text using Google TTS."""
        try:
            # Use English with better accent
            tts = gTTS(text=text, lang='en', tld='com', slow=False)
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
            
            # Run in thread pool to avoid blocking
            import asyncio
            loop = asyncio.get_event_loop()
            
            def sync_convert():
                self.pyttsx3_engine.save_to_file(text, output_path)
                self.pyttsx3_engine.runAndWait()
            
            await loop.run_in_executor(None, sync_convert)
            return os.path.exists(output_path)
            
        except Exception as e:
            logger.error(f"pyttsx3 conversion failed: {e}")
            return False
    
    def _prepare_text_for_tts(self, text: str) -> str:
        """Prepare text for TTS conversion with English optimizations."""
        if not text:
            return ""
        
        # English-specific text preprocessing
        import re
        
        # Handle common abbreviations
        text = re.sub(r'\bDr\.', 'Doctor ', text)
        text = re.sub(r'\bMr\.', 'Mister ', text)
        text = re.sub(r'\bMrs\.', 'Misses ', text)
        text = re.sub(r'\bMs\.', 'Miss ', text)
        text = re.sub(r'\bProf\.', 'Professor ', text)
        text = re.sub(r'\betc\.', 'etcetera', text)
        text = re.sub(r'\bi\.e\.', 'that is', text)
        text = re.sub(r'\be\.g\.', 'for example', text)
        
        # Handle numbers better
        text = re.sub(r'\b(\d+)st\b', r'\1st', text)  # 1st, 21st
        text = re.sub(r'\b(\d+)nd\b', r'\1nd', text)  # 2nd, 22nd
        text = re.sub(r'\b(\d+)rd\b', r'\1rd', text)  # 3rd, 23rd
        text = re.sub(r'\b(\d+)th\b', r'\1th', text)  # 4th, 5th, etc.
        
        # Handle pause markers
        text = text.replace('[pause]', '... ')
        text = text.replace('###', '... ')
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Ensure proper sentence ending
        if not text.endswith(('.', '!', '?')):
            text += '.'
        
        return text
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file system usage."""
        import re
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        filename = filename.strip('._')
        
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename or 'untitled'
    
    def clear_cache(self):
        """Clear the TTS cache."""
        try:
            self.cache.clear()
            logger.info("TTS cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def get_cache_info(self) -> Dict[str, any]:
        """Get cache statistics."""
        try:
            return {
                "cache_size": len(self.cache),
                "cache_directory": self.cache.directory,
                "cache_enabled": self.cache_enabled
            }
        except:
            return {"cache_enabled": False}
    
    @staticmethod
    def get_available_voices() -> Dict[str, List[str]]:
        """Get available voices for each engine."""
        return {
            "coqui-xtts": [
                "tts_models/en/ljspeech/tacotron2-DDC",
                "tts_models/en/vctk/vits",
                "tts_models/en/ljspeech/glow-tts"
            ],
            "edge-tts": [
                "en-US-AriaNeural",
                "en-US-JennyNeural", 
                "en-US-GuyNeural",
                "en-GB-SoniaNeural",
                "en-AU-NatashaNeural"
            ],
            "gtts": ["en"],
            "pyttsx3": ["system_default"]
        }
    
    async def get_voice_sample(self, voice: str, sample_text: str = "Hello, this is a voice sample.") -> str:
        """Generate a voice sample for testing."""
        temp_file = os.path.join(settings.temp_dir, f"sample_{voice.replace('/', '_')}.mp3")
        success = await self.convert_text_to_audio(sample_text, temp_file)
        return temp_file if success else None
    
    def estimate_audio_duration(self, text: str, words_per_minute: int = 150) -> float:
        """Estimate audio duration in seconds."""
        word_count = len(text.split())
        return (word_count / words_per_minute) * 60
    
    def get_engine_info(self) -> Dict[str, any]:
        """Get information about current TTS engine."""
        info = {
            "engine": self.engine,
            "voice": self.voice,
            "coqui_available": COQUI_AVAILABLE,
            "cache_info": self.get_cache_info()
        }
        
        if self.engine == 'coqui-xtts' and self.coqui_tts:
            try:
                import torch
                info["device"] = "cuda" if torch.cuda.is_available() else "cpu"
            except:
                info["device"] = "cpu"
        
        return info 