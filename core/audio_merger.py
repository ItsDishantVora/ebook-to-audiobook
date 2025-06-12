"""Audio merger module for combining multiple audio files into a single audiobook."""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Optional
import subprocess

from pydub import AudioSegment
from pydub.silence import split_on_silence
import ffmpeg

from config import settings

logger = logging.getLogger(__name__)

class AudioMerger:
    """Merge multiple audio files into a single audiobook with metadata."""
    
    def __init__(self):
        self.silence_duration = settings.silence_duration * 1000  # Convert to milliseconds
        self.audio_format = settings.audio_format
        self.audio_quality = settings.audio_quality
        
    async def merge_audio_files(self, audio_files: List[str], output_path: str,
                               metadata: Dict[str, str] = None) -> bool:
        """
        Merge multiple audio files into a single audiobook.
        
        Args:
            audio_files: List of audio file paths to merge
            output_path: Output path for the merged audiobook
            metadata: Book metadata (title, author, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        if not audio_files:
            logger.error("No audio files provided for merging")
            return False
        
        try:
            logger.info(f"Merging {len(audio_files)} audio files into {output_path}")
            
            # Load and combine audio files
            combined_audio = await self._combine_audio_files(audio_files)
            
            if not combined_audio:
                logger.error("Failed to combine audio files")
                return False
            
            # Normalize audio levels
            combined_audio = self._normalize_audio(combined_audio)
            
            # Export with metadata
            success = await self._export_with_metadata(combined_audio, output_path, metadata)
            
            if success:
                logger.info(f"Successfully created audiobook: {output_path}")
                # Log final audio statistics
                duration_minutes = len(combined_audio) / (1000 * 60)
                file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"Audiobook duration: {duration_minutes:.1f} minutes, Size: {file_size_mb:.1f} MB")
            
            return success
            
        except Exception as e:
            logger.error(f"Audio merging failed: {e}")
            return False
    
    async def _combine_audio_files(self, audio_files: List[str]) -> Optional[AudioSegment]:
        """Combine multiple audio files with silence between them."""
        try:
            combined = None
            silence = AudioSegment.silent(duration=self.silence_duration)
            
            for i, audio_file in enumerate(audio_files):
                if not os.path.exists(audio_file):
                    logger.warning(f"Audio file not found: {audio_file}")
                    continue
                
                logger.info(f"Loading audio file {i+1}/{len(audio_files)}: {os.path.basename(audio_file)}")
                
                # Load audio file
                try:
                    audio = AudioSegment.from_file(audio_file)
                except Exception as e:
                    logger.error(f"Failed to load audio file {audio_file}: {e}")
                    continue
                
                # Add to combined audio
                if combined is None:
                    combined = audio
                else:
                    combined = combined + silence + audio
            
            return combined
            
        except Exception as e:
            logger.error(f"Failed to combine audio files: {e}")
            return None
    
    def _normalize_audio(self, audio: AudioSegment) -> AudioSegment:
        """Normalize audio levels for consistent playback."""
        try:
            # Target loudness in dBFS
            target_dbfs = -20.0
            
            # Calculate the change needed
            change_in_dbfs = target_dbfs - audio.dBFS
            
            # Apply normalization
            normalized_audio = audio.apply_gain(change_in_dbfs)
            
            logger.info(f"Audio normalized: {audio.dBFS:.1f} dBFS -> {normalized_audio.dBFS:.1f} dBFS")
            
            return normalized_audio
            
        except Exception as e:
            logger.warning(f"Audio normalization failed: {e}")
            return audio
    
    async def _export_with_metadata(self, audio: AudioSegment, output_path: str,
                                   metadata: Dict[str, str] = None) -> bool:
        """Export audio with metadata using ffmpeg."""
        try:
            # Create temporary file for intermediate processing
            temp_path = output_path + ".temp"
            
            # Export audio to temporary file
            audio.export(
                temp_path,
                format="mp3",
                bitrate=self.audio_quality,
                parameters=["-q:a", "2"]  # High quality encoding
            )
            
            # Add metadata using ffmpeg if available
            if metadata and self._is_ffmpeg_available():
                return await self._add_metadata_with_ffmpeg(temp_path, output_path, metadata)
            else:
                # If no metadata or ffmpeg not available, just move the file
                os.rename(temp_path, output_path)
                return True
                
        except Exception as e:
            logger.error(f"Audio export failed: {e}")
            return False
    
    def _is_ffmpeg_available(self) -> bool:
        """Check if ffmpeg is available on the system."""
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("FFmpeg not available, skipping metadata addition")
            return False
    
    async def _add_metadata_with_ffmpeg(self, input_path: str, output_path: str,
                                       metadata: Dict[str, str]) -> bool:
        """Add metadata to audio file using ffmpeg."""
        try:
            # Build ffmpeg command
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c', 'copy',  # Copy without re-encoding
                '-y'  # Overwrite output file
            ]
            
            # Add metadata
            if metadata.get('title'):
                cmd.extend(['-metadata', f'title={metadata["title"]}'])
            if metadata.get('author'):
                cmd.extend(['-metadata', f'artist={metadata["author"]}'])
                cmd.extend(['-metadata', f'album_artist={metadata["author"]}'])
            if metadata.get('publisher'):
                cmd.extend(['-metadata', f'publisher={metadata["publisher"]}'])
            if metadata.get('language'):
                cmd.extend(['-metadata', f'language={metadata["language"]}'])
            
            # Add generic audiobook metadata
            cmd.extend(['-metadata', 'genre=Audiobook'])
            cmd.extend(['-metadata', 'comment=Generated by Audiobook Converter'])
            
            # Add output file
            cmd.append(output_path)
            
            # Run ffmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Remove temporary file
                os.remove(input_path)
                logger.info("Metadata added successfully")
                return True
            else:
                logger.error(f"FFmpeg failed: {result.stderr}")
                # Fallback: move temp file to output
                os.rename(input_path, output_path)
                return True
                
        except Exception as e:
            logger.error(f"Metadata addition failed: {e}")
            # Fallback: move temp file to output
            try:
                os.rename(input_path, output_path)
                return True
            except:
                return False
    
    def split_audio_by_silence(self, audio_path: str, 
                              min_silence_len: int = 1000,
                              silence_thresh: int = -40) -> List[AudioSegment]:
        """Split audio file by silence (useful for chapter detection)."""
        try:
            audio = AudioSegment.from_file(audio_path)
            chunks = split_on_silence(
                audio,
                min_silence_len=min_silence_len,
                silence_thresh=silence_thresh,
                keep_silence=500  # Keep some silence at the beginning and end
            )
            
            logger.info(f"Split audio into {len(chunks)} segments")
            return chunks
            
        except Exception as e:
            logger.error(f"Audio splitting failed: {e}")
            return []
    
    def get_audio_info(self, audio_path: str) -> Dict[str, any]:
        """Get information about an audio file."""
        try:
            audio = AudioSegment.from_file(audio_path)
            
            return {
                'duration_seconds': len(audio) / 1000,
                'duration_minutes': len(audio) / (1000 * 60),
                'sample_rate': audio.frame_rate,
                'channels': audio.channels,
                'frame_width': audio.frame_width,
                'max_amplitude': audio.max,
                'rms': audio.rms,
                'dbfs': audio.dBFS,
                'file_size_bytes': os.path.getsize(audio_path),
                'file_size_mb': os.path.getsize(audio_path) / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio info: {e}")
            return {}
    
    async def create_chapter_markers(self, audio_files: List[str],
                                   chapter_titles: List[str] = None) -> List[Dict[str, any]]:
        """Create chapter markers for the audiobook."""
        markers = []
        current_time = 0
        
        for i, audio_file in enumerate(audio_files):
            try:
                audio = AudioSegment.from_file(audio_file)
                duration = len(audio) / 1000  # Convert to seconds
                
                title = chapter_titles[i] if chapter_titles and i < len(chapter_titles) else f"Chapter {i+1}"
                
                markers.append({
                    'title': title,
                    'start_time': current_time,
                    'end_time': current_time + duration,
                    'duration': duration
                })
                
                current_time += duration + self.silence_duration / 1000  # Add silence duration
                
            except Exception as e:
                logger.error(f"Failed to process audio file for chapter marker: {e}")
                continue
        
        return markers
    
    def cleanup_temp_files(self, temp_files: List[str]):
        """Clean up temporary audio files."""
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Removed temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {file_path}: {e}")
    
    def validate_audio_file(self, audio_path: str) -> bool:
        """Validate if an audio file is readable."""
        try:
            audio = AudioSegment.from_file(audio_path)
            return len(audio) > 0
        except Exception:
            return False 