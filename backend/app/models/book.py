"""
Book model for storing book information and metadata.
"""
from sqlalchemy import Column, String, DateTime, Text, Integer, JSON, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base

class BookFileType(str, enum.Enum):
    """Enum for supported book file types."""
    PDF = "pdf"
    EPUB = "epub"

class BookStatus(str, enum.Enum):
    """Enum for book processing status."""
    UPLOADED = "uploaded"
    EXTRACTING_TEXT = "extracting_text"
    TEXT_EXTRACTED = "text_extracted"
    PROCESSING_TEXT = "processing_text"
    TEXT_PROCESSED = "text_processed"
    CONVERTING_AUDIO = "converting_audio"
    COMPLETED = "completed"
    FAILED = "failed"

class Book(Base):
    """Book model for storing book information and metadata."""
    
    __tablename__ = "books"
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        unique=True, 
        nullable=False
    )
    
    # Basic book information
    title = Column(String(500), nullable=False)
    author = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    language = Column(String(10), default="en", nullable=False)
    
    # File information
    original_filename = Column(String(255), nullable=False)
    file_type = Column(Enum(BookFileType), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_path = Column(String(500), nullable=False)
    
    # Processing status
    status = Column(Enum(BookStatus), default=BookStatus.UPLOADED, nullable=False)
    
    # Text content
    raw_text = Column(Text, nullable=True)
    processed_text = Column(Text, nullable=True)
    word_count = Column(Integer, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    
    # Chapter information
    chapters = Column(JSON, nullable=True)  # List of chapter objects
    chapter_count = Column(Integer, default=0, nullable=False)
    
    # Audio information
    audio_file_path = Column(String(500), nullable=True)
    audio_file_size = Column(Integer, nullable=True)  # Size in bytes
    audio_duration_seconds = Column(Integer, nullable=True)
    audio_format = Column(String(10), default="mp3", nullable=False)
    
    # Processing metadata
    processing_logs = Column(JSON, nullable=True)  # Processing step logs
    error_message = Column(Text, nullable=True)
    
    # TTS settings used
    tts_voice = Column(String(100), nullable=True)
    tts_speed = Column(String(20), default="normal", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Foreign key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="books")
    conversion_jobs = relationship("ConversionJob", back_populates="book", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Book(id={self.id}, title={self.title}, status={self.status})>"
    
    @property
    def is_processing(self) -> bool:
        """Check if book is currently being processed."""
        processing_statuses = [
            BookStatus.EXTRACTING_TEXT,
            BookStatus.PROCESSING_TEXT,
            BookStatus.CONVERTING_AUDIO
        ]
        return self.status in processing_statuses
    
    @property
    def is_completed(self) -> bool:
        """Check if book processing is completed."""
        return self.status == BookStatus.COMPLETED
    
    @property
    def has_failed(self) -> bool:
        """Check if book processing has failed."""
        return self.status == BookStatus.FAILED
    
    def set_error(self, error_message: str) -> None:
        """Set error status and message."""
        self.status = BookStatus.FAILED
        self.error_message = error_message
    
    def add_processing_log(self, step: str, message: str, success: bool = True) -> None:
        """Add a processing log entry."""
        if self.processing_logs is None:
            self.processing_logs = []
        
        log_entry = {
            "step": step,
            "message": message,
            "success": success,
            "timestamp": func.now()
        }
        self.processing_logs.append(log_entry)
    
    def estimate_duration(self) -> None:
        """Estimate audio duration based on word count."""
        if self.word_count:
            # Average reading speed: 150-200 words per minute
            # TTS is usually a bit slower, so we use 130 words per minute
            self.estimated_duration_minutes = max(1, self.word_count // 130) 