"""
Coqui TTS service for converting text to speech.
"""
import os
import asyncio
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import structlog
from pydub import AudioSegment
import uuid

from app.core.config import settings
from app.core.exceptions import TTSError

logger = structlog.get_logger()

class TTSService:
    """Service for converting text to speech using Coqui TTS."""
    
    def __init__(self):
        self.tts_model = None
        self.available_voices = []
        self._initialize_tts()
    
    def _initialize_tts(self):
        """Initialize Coqui TTS model."""
        try:
            from TTS.api import TTS
            
            # Initialize with a pre-trained model
            model_name = settings.TTS_MODEL_NAME
            logger.info("Initializing TTS model", model=model_name)
            
            self.tts_model = TTS(
                model_name=model_name,
                progress_bar=False,
                gpu=False  # Set to True if you have GPU support
            )
            
            # Get available voices for the model
            if hasattr(self.tts_model, 'speakers'):
                self.available_voices = self.tts_model.speakers or ["default"]
            else:
                self.available_voices = ["default"]
            
            logger.info("TTS service initialized successfully", 
                       voices=len(self.available_voices))
            
        except Exception as e:
            logger.error("Failed to initialize TTS service", error=str(e))
            self.tts_model = None
    
    async def convert_text_to_audio(
        self, 
        text: str, 
        output_path: str, 
        voice: str = None,
        speed: float = 1.0,
        chunk_size: int = 1000
    ) -> Dict[str, any]:
        """
        Convert text to audio file.
        
        Args:
            text: Text to convert
            output_path: Path where to save the audio file
            voice: Voice to use (optional)
            speed: Speech speed multiplier
            chunk_size: Size of text chunks for processing
            
        Returns:
            Dictionary with conversion results
        """
        if not self.tts_model:
            raise TTSError("TTS service not initialized")
        
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Split text into manageable chunks
            text_chunks = self._split_text_for_tts(text, chunk_size)
            
            if not text_chunks:
                raise TTSError("No text to convert")
            
            logger.info("Starting TTS conversion", 
                       chunks=len(text_chunks), 
                       total_chars=len(text))
            
            # Convert each chunk to audio
            audio_files = []
            for i, chunk in enumerate(text_chunks):
                chunk_file = f"{output_path}_chunk_{i}.wav"
                
                logger.info(f"Converting chunk {i+1}/{len(text_chunks)}")
                await self._convert_chunk_to_audio(chunk, chunk_file, voice)
                audio_files.append(chunk_file)
            
            # Combine all audio chunks
            final_audio = await self._combine_audio_files(audio_files, output_path)
            
            # Clean up temporary chunk files
            for chunk_file in audio_files:
                try:
                    os.remove(chunk_file)
                except Exception:
                    pass
            
            # Apply speed adjustment if needed
            if speed != 1.0:
                await self._adjust_audio_speed(output_path, speed)
            
            # Get audio file info
            audio_info = await self._get_audio_info(output_path)
            
            logger.info("TTS conversion completed successfully", 
                       output_file=output_path,
                       duration=audio_info.get('duration_seconds'))
            
            return {
                "success": True,
                "output_file": output_path,
                "duration_seconds": audio_info.get('duration_seconds'),
                "file_size_bytes": audio_info.get('file_size_bytes'),
                "chunks_processed": len(text_chunks),
                "voice_used": voice or "default"
            }
            
        except Exception as e:
            logger.error("TTS conversion failed", error=str(e))
            raise TTSError(f"Failed to convert text to audio: {str(e)}")
    
    async def _convert_chunk_to_audio(self, text: str, output_file: str, voice: str = None):
        """Convert a single text chunk to audio."""
        
        try:
            # Run TTS in a thread to avoid blocking
            await asyncio.to_thread(
                self._tts_to_file,
                text,
                output_file,
                voice
            )
            
        except Exception as e:
            logger.error("Chunk conversion failed", error=str(e))
            raise TTSError(f"Failed to convert text chunk: {str(e)}")
    
    def _tts_to_file(self, text: str, file_path: str, voice: str = None):
        """Synchronous TTS conversion."""
        
        try:
            if voice and voice in self.available_voices:
                self.tts_model.tts_to_file(
                    text=text,
                    file_path=file_path,
                    speaker=voice
                )
            else:
                self.tts_model.tts_to_file(
                    text=text,
                    file_path=file_path
                )
        except Exception as e:
            raise TTSError(f"TTS conversion error: {str(e)}")
    
    async def _combine_audio_files(self, audio_files: List[str], output_path: str) -> AudioSegment:
        """Combine multiple audio files into one."""
        
        try:
            combined_audio = AudioSegment.empty()
            
            for audio_file in audio_files:
                if os.path.exists(audio_file):
                    audio_segment = AudioSegment.from_wav(audio_file)
                    combined_audio += audio_segment
                    
                    # Add small pause between chunks (250ms)
                    silence = AudioSegment.silent(duration=250)
                    combined_audio += silence
            
            if not combined_audio:
                raise TTSError("No audio content to combine")
            
            # Export as MP3
            combined_audio.export(output_path, format="mp3", bitrate="128k")
            
            return combined_audio
            
        except Exception as e:
            logger.error("Audio combination failed", error=str(e))
            raise TTSError(f"Failed to combine audio files: {str(e)}")
    
    async def _adjust_audio_speed(self, audio_file: str, speed: float):
        """Adjust audio playback speed."""
        
        try:
            audio = AudioSegment.from_mp3(audio_file)
            
            # Change speed by changing frame rate
            new_sample_rate = int(audio.frame_rate * speed)
            speed_adjusted_audio = audio._spawn(audio.raw_data, overrides={
                "frame_rate": new_sample_rate
            })
            
            # Set back to original frame rate to maintain pitch
            speed_adjusted_audio = speed_adjusted_audio.set_frame_rate(audio.frame_rate)
            
            # Export back to file
            speed_adjusted_audio.export(audio_file, format="mp3", bitrate="128k")
            
        except Exception as e:
            logger.error("Speed adjustment failed", error=str(e))
            # Non-critical error, continue without speed adjustment
    
    async def _get_audio_info(self, audio_file: str) -> Dict[str, any]:
        """Get information about the audio file."""
        
        try:
            audio = AudioSegment.from_mp3(audio_file)
            file_size = os.path.getsize(audio_file)
            
            return {
                "duration_seconds": len(audio) / 1000.0,  # Convert from milliseconds
                "file_size_bytes": file_size,
                "sample_rate": audio.frame_rate,
                "channels": audio.channels,
                "format": "mp3"
            }
            
        except Exception as e:
            logger.error("Failed to get audio info", error=str(e))
            return {
                "duration_seconds": 0,
                "file_size_bytes": os.path.getsize(audio_file) if os.path.exists(audio_file) else 0
            }
    
    def _split_text_for_tts(self, text: str, max_chunk_size: int = 1000) -> List[str]:
        """Split text into chunks suitable for TTS processing."""
        
        # Split by sentences first
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # If adding this sentence would exceed chunk size
            if current_size + sentence_size > max_chunk_size and current_chunk:
                # Finish current chunk
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add the last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        # Filter out empty chunks
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        
        import re
        
        # Simple sentence splitting (can be improved with NLTK)
        # Split on periods, exclamation marks, question marks
        sentences = re.split(r'[.!?]+', text)
        
        # Clean up and filter
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                # Add back the punctuation
                if not sentence.endswith(('.', '!', '?')):
                    sentence += '.'
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def get_available_voices(self) -> List[str]:
        """Get list of available voices."""
        return self.available_voices.copy()
    
    def is_available(self) -> bool:
        """Check if TTS service is available."""
        return self.tts_model is not None
    
    async def estimate_conversion_time(self, text_length: int) -> int:
        """Estimate conversion time in seconds based on text length."""
        
        # Rough estimation: 1 character takes about 0.1 seconds to process
        # This varies greatly based on hardware and model
        base_time = text_length * 0.1
        
        # Add overhead for chunk processing and combining
        overhead = min(60, text_length / 1000 * 10)  # Max 60 seconds overhead
        
        return int(base_time + overhead)
    
    async def convert_with_progress_callback(
        self,
        text: str,
        output_path: str,
        progress_callback=None,
        voice: str = None,
        speed: float = 1.0
    ) -> Dict[str, any]:
        """
        Convert text to audio with progress reporting.
        
        Args:
            text: Text to convert
            output_path: Output file path
            progress_callback: Function to call with progress updates
            voice: Voice to use
            speed: Speech speed
            
        Returns:
            Conversion results
        """
        if not self.tts_model:
            raise TTSError("TTS service not initialized")
        
        # Split text into chunks
        text_chunks = self._split_text_for_tts(text)
        total_chunks = len(text_chunks)
        
        if progress_callback:
            await progress_callback(0, f"Starting conversion of {total_chunks} chunks")
        
        # Process chunks with progress reporting
        audio_files = []
        for i, chunk in enumerate(text_chunks):
            chunk_file = f"{output_path}_chunk_{i}.wav"
            
            if progress_callback:
                progress = (i / total_chunks) * 80  # 80% for chunk processing
                await progress_callback(progress, f"Converting chunk {i+1}/{total_chunks}")
            
            await self._convert_chunk_to_audio(chunk, chunk_file, voice)
            audio_files.append(chunk_file)
        
        if progress_callback:
            await progress_callback(85, "Combining audio chunks")
        
        # Combine chunks
        await self._combine_audio_files(audio_files, output_path)
        
        if progress_callback:
            await progress_callback(95, "Finalizing audio file")
        
        # Cleanup and finalize
        for chunk_file in audio_files:
            try:
                os.remove(chunk_file)
            except Exception:
                pass
        
        if speed != 1.0:
            await self._adjust_audio_speed(output_path, speed)
        
        audio_info = await self._get_audio_info(output_path)
        
        if progress_callback:
            await progress_callback(100, "Conversion completed")
        
        return {
            "success": True,
            "output_file": output_path,
            "duration_seconds": audio_info.get('duration_seconds'),
            "file_size_bytes": audio_info.get('file_size_bytes'),
            "chunks_processed": total_chunks,
            "voice_used": voice or "default"
        } 