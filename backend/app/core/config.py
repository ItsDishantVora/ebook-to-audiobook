"""
Configuration settings for the AudioBook Converter application.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    PROJECT_NAME: str = "AudioBook Converter API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    
    # CORS
    ALLOWED_HOSTS: str = "*"  # Change for production
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://user:password@localhost:5432/audiobook_db"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # AI Services
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # File Upload
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    UPLOAD_DIR: str = "uploads"
    AUDIO_OUTPUT_DIR: str = "audio_output"
    
    # TTS Configuration
    TTS_MODEL_NAME: str = "tts_models/en/ljspeech/tacotron2-DDC"
    TTS_VOCODER_NAME: Optional[str] = None
    
    # Celery Configuration
    CELERY_BROKER_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # JWT Configuration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Development/Production
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    def get_allowed_hosts(self) -> List[str]:
        """Get parsed CORS origins."""
        if self.ALLOWED_HOSTS == "*":
            return ["*"]
        return [i.strip() for i in self.ALLOWED_HOSTS.split(",") if i.strip()]
    
    class Config:
        case_sensitive = True
        env_file = ".env"

# Create global settings instance
settings = Settings() 