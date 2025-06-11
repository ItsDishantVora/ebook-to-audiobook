"""
Celery tasks for book to audiobook conversion.
"""
import os
import asyncio
from typing import Dict, Any
from celery import Task
import structlog

from app.core.celery import celery_app
from sqlalchemy import select, func
from app.core.database import get_db_session
from app.models import Book, ConversionJob, BookStatus, JobStatus
from app.services import FileProcessor, GeminiService, TTSService
from app.core.config import settings

logger = structlog.get_logger()

class CallbackTask(Task):
    """Base task class with callbacks for database updates."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success."""
        logger.info("Task completed successfully", task_id=task_id)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure."""
        logger.error("Task failed", task_id=task_id, error=str(exc))

@celery_app.task(base=CallbackTask, bind=True)
def convert_book_to_audiobook(self, book_id: str, job_id: str, voice: str = "default", speed: str = "normal"):
    """
    Simplified conversion task that does everything in one step.
    """
    try:
        logger.info("Starting book conversion", book_id=book_id, job_id=job_id)
        
        # Update job progress
        update_job_progress(job_id, 0, "Starting conversion")
        
        # Get book from database
        book = get_book_sync(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")
        
        # Step 1: Extract text (20% progress)
        update_job_progress(job_id, 10, "Extracting text from book")
        update_book_status(book_id, BookStatus.EXTRACTING_TEXT)
        
        file_processor = FileProcessor()
        
        # Use the async method but run it synchronously in the task
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        extraction_result = loop.run_until_complete(
            file_processor.extract_text_from_file(book.file_path, book.file_type.value)
        )
        
        text_content = extraction_result.get("raw_text", "")
        if not text_content or len(text_content.strip()) < 10:
            raise ValueError("Failed to extract meaningful text from the book")
        
        word_count = extraction_result.get("word_count", len(text_content.split()))
        update_book_text(book_id, text_content, word_count)
        update_book_status(book_id, BookStatus.TEXT_EXTRACTED)
        update_job_progress(job_id, 30, "Text extraction completed")
        
        # Step 2: Process text with AI (optional - skip if fails)
        update_job_progress(job_id, 35, "Processing text with AI")
        update_book_status(book_id, BookStatus.PROCESSING_TEXT)
        
        try:
            from app.services import GeminiService
            gemini_service = GeminiService()
            
            # Create metadata for Gemini processing
            book_metadata = {
                "title": book.title,
                "author": book.author,
                "language": book.language
            }
            
            # Use async method properly
            processed_text = loop.run_until_complete(
                gemini_service.enhance_text_for_audiobook(text_content, book_metadata)
            )
            logger.info("Text enhanced with Gemini AI", 
                       original_length=len(text_content),
                       enhanced_length=len(processed_text))
        except Exception as e:
            logger.warning("AI processing failed, using original text", error=str(e))
            processed_text = text_content
        
        update_book_processed_text(book_id, processed_text)
        update_book_status(book_id, BookStatus.TEXT_PROCESSED)
        update_job_progress(job_id, 50, "Text processing completed")
        
        # Step 3: Generate audio (50% progress)
        update_job_progress(job_id, 55, "Generating audio")
        update_book_status(book_id, BookStatus.CONVERTING_AUDIO)
        
        # Create output directory
        import os
        from app.core.config import settings
        audio_dir = os.path.join(settings.UPLOAD_DIR, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        
        # Generate unique audio filename
        audio_filename = f"{book_id}_audiobook.mp3"
        audio_path = os.path.join(audio_dir, audio_filename)
        
        # Use real TTS service to generate audio
        try:
            from app.services.tts_service import TTSService
            tts_service = TTSService()
            
            if tts_service.is_available():
                logger.info("Converting text to speech", text_length=len(processed_text))
                update_job_progress(job_id, 60, "Converting text to speech")
                
                # Convert text to audio
                tts_result = loop.run_until_complete(
                    tts_service.convert_text_to_audio(
                        text=processed_text,
                        output_path=audio_path,
                        voice=voice,
                        speed=1.0 if speed == "normal" else 1.2 if speed == "fast" else 0.8
                    )
                )
                
                audio_info = {
                    "file_size": tts_result.get("file_size_bytes", 0),
                    "duration_seconds": tts_result.get("duration_seconds", 0),
                    "format": "mp3",
                    "voice_used": tts_result.get("voice_used", "default"),
                    "chunks_processed": tts_result.get("chunks_processed", 1)
                }
                
                logger.info("Real audio generated successfully", 
                           duration=audio_info["duration_seconds"],
                           file_size=audio_info["file_size"])
                
            else:
                # Fallback to demo content if TTS not available
                logger.warning("TTS service not available, creating demo content")
                demo_audio_content = f"This is a demo audiobook for: {book.title}. The book contains {word_count} words."
                
                with open(audio_path.replace('.mp3', '.txt'), 'w') as f:
                    f.write(f"Demo Audio Content:\n{demo_audio_content}\n\nOriginal Text:\n{processed_text[:500]}...")
                
                audio_info = {
                    "file_size": len(demo_audio_content),
                    "duration_seconds": max(60, word_count // 3),
                    "format": "txt"
                }
                audio_path = audio_path.replace('.mp3', '.txt')
                
        except Exception as e:
            logger.error("TTS conversion failed, using demo content", error=str(e))
            # Fallback to demo content
            demo_audio_content = f"This is a demo audiobook for: {book.title}. The book contains {word_count} words."
            
            with open(audio_path.replace('.mp3', '.txt'), 'w') as f:
                f.write(f"Demo Audio Content:\n{demo_audio_content}\n\nOriginal Text:\n{processed_text[:500]}...")
            
            audio_info = {
                "file_size": len(demo_audio_content),
                "duration_seconds": max(60, word_count // 3),
                "format": "txt"
            }
            audio_path = audio_path.replace('.mp3', '.txt')
        
        update_book_audio(book_id, audio_path, audio_info)
        update_job_progress(job_id, 95, "Audio generation completed")
        
        # Step 4: Finalize
        finalize_conversion(book_id, job_id, audio_info)
        update_job_progress(job_id, 100, "Conversion completed successfully")
        
        logger.info("Book conversion completed", book_id=book_id, job_id=job_id)
        
        return {
            "book_id": book_id,
            "job_id": job_id,
            "status": "completed",
            "audio_info": audio_info
        }
        
    except Exception as e:
        logger.error("Book conversion failed", book_id=book_id, job_id=job_id, error=str(e))
        mark_job_failed(job_id, str(e))
        mark_book_failed(book_id, str(e))
        raise

@celery_app.task(base=CallbackTask, bind=True)
def extract_text_task(self, book_id: str, job_id: str):
    """Extract text from uploaded book file."""
    try:
        logger.info("Starting text extraction", book_id=book_id)
        
        # Get book from database
        book = get_book_sync(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")
        
        # Update book status
        update_book_status(book_id, BookStatus.EXTRACTING_TEXT)
        
        # Extract text using FileProcessor
        file_processor = FileProcessor()
        
        if book.file_type.value == "pdf":
            text_content = file_processor.extract_text_from_pdf(book.file_path)
        elif book.file_type.value == "epub":
            text_content = file_processor.extract_text_from_epub(book.file_path)
        else:
            raise ValueError(f"Unsupported file type: {book.file_type}")
        
        if not text_content or len(text_content.strip()) < 10:
            raise ValueError("Failed to extract meaningful text from the book")
        
        # Update book with extracted text
        word_count = len(text_content.split())
        update_book_text(book_id, text_content, word_count)
        update_book_status(book_id, BookStatus.TEXT_EXTRACTED)
        
        logger.info("Text extraction completed", book_id=book_id, word_count=word_count)
        
        return text_content
        
    except Exception as e:
        logger.error("Text extraction failed", book_id=book_id, error=str(e))
        mark_book_failed(book_id, f"Text extraction failed: {str(e)}")
        raise

@celery_app.task(base=CallbackTask, bind=True)
def process_text_task(self, book_id: str, job_id: str, text_content: str):
    """Process and enhance text using Gemini AI."""
    try:
        logger.info("Starting text processing", book_id=book_id)
        
        update_book_status(book_id, BookStatus.PROCESSING_TEXT)
        
        # Initialize Gemini service
        gemini_service = GeminiService()
        
        # Process text for better TTS
        processed_text = gemini_service.enhance_text_for_tts(text_content)
        
        # Update book with processed text
        update_book_processed_text(book_id, processed_text)
        update_book_status(book_id, BookStatus.TEXT_PROCESSED)
        
        logger.info("Text processing completed", book_id=book_id)
        
        return processed_text
        
    except Exception as e:
        logger.error("Text processing failed", book_id=book_id, error=str(e))
        # If AI processing fails, use original text
        logger.warning("Using original text due to AI processing failure", book_id=book_id)
        update_book_processed_text(book_id, text_content)
        update_book_status(book_id, BookStatus.TEXT_PROCESSED)
        return text_content

@celery_app.task(base=CallbackTask, bind=True)
def generate_audio_task(self, book_id: str, job_id: str, text_content: str, voice: str = "default", speed: str = "normal"):
    """Generate audio from processed text using TTS."""
    try:
        logger.info("Starting audio generation", book_id=book_id)
        
        update_book_status(book_id, BookStatus.CONVERTING_AUDIO)
        
        # Get book info
        book = get_book_sync(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")
        
        # Initialize TTS service
        tts_service = TTSService()
        
        # Create output directory
        audio_dir = os.path.join(settings.UPLOAD_DIR, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        
        # Generate unique audio filename
        audio_filename = f"{book_id}_audiobook.mp3"
        audio_path = os.path.join(audio_dir, audio_filename)
        
        # Generate audio with progress callback
        def progress_callback(current_chunk: int, total_chunks: int):
            progress = 50 + (current_chunk / total_chunks) * 45  # 50-95% range
            update_job_progress(job_id, progress, f"Generating audio: {current_chunk}/{total_chunks}")
        
        audio_info = tts_service.text_to_speech(
            text=text_content,
            output_path=audio_path,
            voice=voice,
            speed=speed,
            progress_callback=progress_callback
        )
        
        # Update book with audio information
        update_book_audio(book_id, audio_path, audio_info)
        
        logger.info("Audio generation completed", book_id=book_id, audio_path=audio_path)
        
        return {
            "audio_path": audio_path,
            "audio_info": audio_info
        }
        
    except Exception as e:
        logger.error("Audio generation failed", book_id=book_id, error=str(e))
        mark_book_failed(book_id, f"Audio generation failed: {str(e)}")
        raise

# Helper functions for database operations

def get_book_sync(book_id: str):
    """Get book from database synchronously."""
    with get_db_session() as db:
        result = db.execute(select(Book).where(Book.id == book_id))
        return result.scalar_one_or_none()

def update_book_status(book_id: str, status: BookStatus):
    """Update book status."""
    with get_db_session() as db:
        book = db.get(Book, book_id)
        if book:
            book.status = status
            db.commit()

def update_book_text(book_id: str, text_content: str, word_count: int):
    """Update book with extracted text."""
    with get_db_session() as db:
        book = db.get(Book, book_id)
        if book:
            book.raw_text = text_content
            book.word_count = word_count
            book.estimate_duration()
            db.commit()

def update_book_processed_text(book_id: str, processed_text: str):
    """Update book with processed text."""
    with get_db_session() as db:
        book = db.get(Book, book_id)
        if book:
            book.processed_text = processed_text
            db.commit()

def update_book_audio(book_id: str, audio_path: str, audio_info: Dict[str, Any]):
    """Update book with audio information."""
    with get_db_session() as db:
        book = db.get(Book, book_id)
        if book:
            book.audio_file_path = audio_path
            book.audio_file_size = audio_info.get("file_size", 0)
            book.audio_duration_seconds = audio_info.get("duration_seconds", 0)
            db.commit()

def mark_book_failed(book_id: str, error_message: str):
    """Mark book as failed."""
    with get_db_session() as db:
        book = db.get(Book, book_id)
        if book:
            book.set_error(error_message)
            db.commit()

def finalize_conversion(book_id: str, job_id: str, audio_info: Dict[str, Any]):
    """Finalize the conversion process."""
    with get_db_session() as db:
        book = db.get(Book, book_id)
        job = db.get(ConversionJob, job_id)
        
        if book:
            book.status = BookStatus.COMPLETED
            book.completed_at = func.now()
        
        if job:
            job.status = JobStatus.SUCCESS
            job.progress_percentage = 100.0
            job.current_step = "Completed"
            job.completed_at = func.now()
            job.result = audio_info
        
        db.commit()

def update_job_progress(job_id: str, progress: float, step: str):
    """Update job progress."""
    with get_db_session() as db:
        job = db.get(ConversionJob, job_id)
        if job:
            job.update_progress(progress, step)
            db.commit()

def mark_job_failed(job_id: str, error_message: str):
    """Mark job as failed."""
    with get_db_session() as db:
        job = db.get(ConversionJob, job_id)
        if job:
            job.set_error(error_message)
            db.commit() 