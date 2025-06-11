"""
User model for authentication and user management.
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base

class User(Base):
    """User model for storing user information."""
    
    __tablename__ = "users"
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        unique=True, 
        nullable=False
    )
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Usage limits
    monthly_conversion_limit = Column(Integer, default=10, nullable=False)
    monthly_conversions_used = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    books = relationship("Book", back_populates="user", cascade="all, delete-orphan")
    conversion_jobs = relationship("ConversionJob", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
    
    @property
    def has_remaining_conversions(self) -> bool:
        """Check if user has remaining conversions for the month."""
        return self.monthly_conversions_used < self.monthly_conversion_limit
    
    def increment_conversion_count(self) -> None:
        """Increment the monthly conversion count."""
        self.monthly_conversions_used += 1
    
    def reset_monthly_conversions(self) -> None:
        """Reset monthly conversion count (called by cron job)."""
        self.monthly_conversions_used = 0 