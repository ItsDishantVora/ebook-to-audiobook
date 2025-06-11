"""
ConversionJob model for tracking background conversion tasks.
"""
from sqlalchemy import Column, String, DateTime, Text, JSON, Enum, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base

class JobStatus(str, enum.Enum):
    """Enum for conversion job status."""
    PENDING = "pending"
    STARTED = "started"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"

class JobType(str, enum.Enum):
    """Enum for conversion job types."""
    TEXT_EXTRACTION = "text_extraction"
    TEXT_PROCESSING = "text_processing"
    TTS_CONVERSION = "tts_conversion"
    FULL_CONVERSION = "full_conversion"

class ConversionJob(Base):
    """ConversionJob model for tracking background processing tasks."""
    
    __tablename__ = "conversion_jobs"
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        unique=True, 
        nullable=False
    )
    
    # Job identification
    celery_task_id = Column(String(255), unique=True, index=True, nullable=True)
    job_type = Column(Enum(JobType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    
    # Progress tracking
    progress_percentage = Column(Float, default=0.0, nullable=False)
    current_step = Column(String(255), nullable=True)
    total_steps = Column(Integer, nullable=True)
    
    # Job details
    parameters = Column(JSON, nullable=True)  # Job-specific parameters
    result = Column(JSON, nullable=True)  # Job result data
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # Retry mechanism
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Timing information
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Estimated and actual duration
    estimated_duration_seconds = Column(Integer, nullable=True)
    actual_duration_seconds = Column(Integer, nullable=True)
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="conversion_jobs")
    book = relationship("Book", back_populates="conversion_jobs")
    
    def __repr__(self) -> str:
        return f"<ConversionJob(id={self.id}, type={self.job_type}, status={self.status})>"
    
    @property
    def is_completed(self) -> bool:
        """Check if job is completed (success or failure)."""
        return self.status in [JobStatus.SUCCESS, JobStatus.FAILURE]
    
    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status in [JobStatus.STARTED, JobStatus.PROCESSING]
    
    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (
            self.status == JobStatus.FAILURE and 
            self.retry_count < self.max_retries
        )
    
    def update_progress(self, percentage: float, step: str = None) -> None:
        """Update job progress."""
        self.progress_percentage = min(100.0, max(0.0, percentage))
        if step:
            self.current_step = step
        
        if percentage >= 100.0:
            self.status = JobStatus.SUCCESS
            self.completed_at = func.now()
    
    def set_error(self, error_message: str, traceback: str = None) -> None:
        """Set job error status."""
        self.status = JobStatus.FAILURE
        self.error_message = error_message
        self.error_traceback = traceback
        self.completed_at = func.now()
    
    def increment_retry(self) -> None:
        """Increment retry count."""
        self.retry_count += 1
        if self.retry_count < self.max_retries:
            self.status = JobStatus.RETRY
        else:
            self.status = JobStatus.FAILURE
    
    def start_job(self, celery_task_id: str = None) -> None:
        """Mark job as started."""
        self.status = JobStatus.STARTED
        self.started_at = func.now()
        if celery_task_id:
            self.celery_task_id = celery_task_id
    
    def calculate_duration(self) -> None:
        """Calculate actual job duration."""
        if self.started_at and self.completed_at:
            duration = self.completed_at - self.started_at
            self.actual_duration_seconds = int(duration.total_seconds())
    
    def get_eta_seconds(self) -> int:
        """Get estimated time to completion in seconds."""
        if not self.estimated_duration_seconds:
            return None
        
        if self.progress_percentage == 0:
            return self.estimated_duration_seconds
        
        # Calculate based on current progress
        elapsed_time = 0
        if self.started_at:
            elapsed_time = (func.now() - self.started_at).total_seconds()
        
        if self.progress_percentage > 0:
            estimated_total = elapsed_time / (self.progress_percentage / 100)
            return max(0, int(estimated_total - elapsed_time))
        
        return self.estimated_duration_seconds 