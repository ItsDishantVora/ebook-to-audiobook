import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # API Keys
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    
    # TTS Configuration
    tts_engine: str = os.getenv("TTS_ENGINE", "edge-tts")
    default_voice: str = os.getenv("DEFAULT_VOICE", "en-US-AriaNeural")
    speech_rate: float = float(os.getenv("SPEECH_RATE", "1.0"))
    
    # Audio Configuration
    audio_format: str = os.getenv("AUDIO_FORMAT", "mp3")
    audio_quality: str = os.getenv("AUDIO_QUALITY", "128k")
    silence_duration: float = float(os.getenv("SILENCE_DURATION", "2.0"))
    
    # Processing Configuration
    max_chunk_size: int = int(os.getenv("MAX_CHUNK_SIZE", "30000"))
    temp_dir: str = os.getenv("TEMP_DIR", "temp")
    output_dir: str = os.getenv("OUTPUT_DIR", "output")
    max_concurrent_requests: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
    
    # Debug Configuration
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Gemini Configuration
    gemini_model: str = "gemini-1.5-flash"  # Cost-effective model
    gemini_temperature: float = 0.1
    gemini_max_tokens: int = 8192
    
    # TTS Voice Options
    available_voices: dict = {
        "en-US-AriaNeural": "English (US) - Aria",
        "en-US-JennyNeural": "English (US) - Jenny",
        "en-US-GuyNeural": "English (US) - Guy",
        "en-GB-SoniaNeural": "English (UK) - Sonia",
        "en-AU-NatashaNeural": "English (AU) - Natasha",
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Create directories if they don't exist
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Validate API key
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required. Please set it in your .env file.")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings() 