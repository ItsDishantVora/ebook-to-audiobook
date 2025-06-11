"""
Book management endpoints.
"""
import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.models import Book, User, BookFileType, BookStatus
from app.services import FileProcessor
from app.core.config import settings

router = APIRouter()
logger = structlog.get_logger()

# Supported file types
SUPPORTED_EXTENSIONS = {".pdf", ".epub"}
MAX_FILE_SIZE = settings.MAX_FILE_SIZE  # 100MB

@router.post("/upload")
async def upload_book(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    author: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    language: str = Form("en"),
    db: AsyncSession = Depends(get_db)
):
    """Upload a new book file (PDF or EPUB)."""
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    
    # Check file size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    try:
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(settings.UPLOAD_DIR)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_path = os.path.join(upload_dir, f"{file_id}{file_extension}")
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Determine file type
        file_type = BookFileType.PDF if file_extension == ".pdf" else BookFileType.EPUB
        
        # Create or get dummy user for testing
        from app.models import User
        dummy_user_id = "00000000-0000-0000-0000-000000000001"
        
        # Check if dummy user exists, create if not
        result = await db.execute(select(User).where(User.id == dummy_user_id))
        dummy_user = result.scalar_one_or_none()
        
        if not dummy_user:
            dummy_user = User(
                id=dummy_user_id,
                email="test@audiobook.com",
                username="testuser",
                full_name="Test User",
                hashed_password="dummy_hash_for_testing",
                is_active=True
            )
            db.add(dummy_user)
            await db.commit()
        
        book = Book(
            title=title,
            author=author,
            description=description,
            language=language,
            original_filename=file.filename,
            file_type=file_type,
            file_size=len(file_content),
            file_path=file_path,
            status=BookStatus.UPLOADED,
            user_id=dummy_user_id
        )
        
        db.add(book)
        await db.commit()
        await db.refresh(book)
        
        logger.info("Book uploaded successfully", book_id=str(book.id), title=title)
        
        # Start background text extraction
        background_tasks.add_task(start_text_extraction, str(book.id))
        
        return {
            "message": "Book uploaded successfully",
            "book_id": str(book.id),
            "title": title,
            "file_type": file_type.value,
            "file_size": len(file_content),
            "status": book.status.value
        }
        
    except Exception as e:
        logger.error("Failed to upload book", error=str(e))
        # Clean up file if database operation failed
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Failed to upload book")

@router.get("/")
async def get_books(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get list of books."""
    try:
        # For now, get all books - later filter by user
        result = await db.execute(
            select(Book).offset(skip).limit(limit).order_by(Book.created_at.desc())
        )
        books = result.scalars().all()
        
        return {
            "books": [
                {
                    "id": str(book.id),
                    "title": book.title,
                    "author": book.author,
                    "status": book.status.value,
                    "file_type": book.file_type.value,
                    "created_at": book.created_at.isoformat(),
                    "word_count": book.word_count,
                    "estimated_duration_minutes": book.estimated_duration_minutes
                }
                for book in books
            ],
            "total": len(books)
        }
    except Exception as e:
        logger.error("Failed to get books", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve books")

@router.get("/{book_id}")
async def get_book(
    book_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed book information."""
    try:
        result = await db.execute(select(Book).where(Book.id == book_id))
        book = result.scalar_one_or_none()
        
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        return {
            "id": str(book.id),
            "title": book.title,
            "author": book.author,
            "description": book.description,
            "language": book.language,
            "status": book.status.value,
            "file_type": book.file_type.value,
            "file_size": book.file_size,
            "word_count": book.word_count,
            "estimated_duration_minutes": book.estimated_duration_minutes,
            "chapter_count": book.chapter_count,
            "created_at": book.created_at.isoformat(),
            "updated_at": book.updated_at.isoformat(),
            "processing_logs": book.processing_logs,
            "error_message": book.error_message,
            "audio_duration_seconds": book.audio_duration_seconds
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get book", book_id=book_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve book")

@router.delete("/{book_id}")
async def delete_book(
    book_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a book and its associated files."""
    try:
        result = await db.execute(select(Book).where(Book.id == book_id))
        book = result.scalar_one_or_none()
        
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Delete files
        if book.file_path and os.path.exists(book.file_path):
            os.remove(book.file_path)
        
        if book.audio_file_path and os.path.exists(book.audio_file_path):
            os.remove(book.audio_file_path)
        
        # Delete from database
        await db.delete(book)
        await db.commit()
        
        logger.info("Book deleted successfully", book_id=book_id)
        
        return {"message": "Book deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete book", book_id=book_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete book")

@router.get("/{book_id}/download")
async def download_audiobook(
    book_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Download the converted audiobook."""
    try:
        result = await db.execute(select(Book).where(Book.id == book_id))
        book = result.scalar_one_or_none()
        
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        if not book.is_completed:
            raise HTTPException(
                status_code=400, 
                detail=f"Book conversion not completed. Current status: {book.status.value}"
            )
        
        if not book.audio_file_path or not os.path.exists(book.audio_file_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        filename = f"{book.title.replace(' ', '_')}_audiobook.{book.audio_format}"
        
        return FileResponse(
            path=book.audio_file_path,
            filename=filename,
            media_type=f"audio/{book.audio_format}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download audiobook", book_id=book_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to download audiobook")

async def start_text_extraction(book_id: str):
    """Background task to start text extraction."""
    # This will be implemented with Celery tasks
    # For now, just log the action
    logger.info("Starting text extraction", book_id=book_id) 