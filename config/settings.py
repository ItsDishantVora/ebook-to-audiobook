import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # API Keys
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    
    # TTS Configuration - Prioritize Coqui TTS for best quality
    tts_engine: str = os.getenv("TTS_ENGINE", "coqui-xtts")  # Changed default
    default_voice: str = os.getenv("DEFAULT_VOICE", "tts_models/en/ljspeech/tacotron2-DDC")
    fallback_engine: str = os.getenv("FALLBACK_ENGINE", "edge-tts")
    fallback_voice: str = os.getenv("FALLBACK_VOICE", "en-US-AriaNeural")
    speech_rate: float = float(os.getenv("SPEECH_RATE", "1.0"))
    
    # Audio Configuration
    audio_format: str = os.getenv("AUDIO_FORMAT", "mp3")
    audio_quality: str = os.getenv("AUDIO_QUALITY", "128k")
    silence_duration: float = float(os.getenv("SILENCE_DURATION", "2.0"))
    
    # Processing Configuration
    max_chunk_size: int = int(os.getenv("MAX_CHUNK_SIZE", "30000"))
    temp_dir: str = os.getenv("TEMP_DIR", "temp")
    output_dir: str = os.getenv("OUTPUT_DIR", "output")
    max_concurrent_requests: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "3"))  # Reduced for Coqui TTS
    
    # Caching Configuration
    enable_tts_cache: bool = os.getenv("ENABLE_TTS_CACHE", "True").lower() == "true"
    cache_max_size: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))  # Max cached items
    cache_ttl: int = int(os.getenv("CACHE_TTL", "86400"))  # 24 hours
    
    # Debug Configuration
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Gemini Configuration
    gemini_model: str = "gemini-1.5-flash"  # Cost-effective model
    gemini_temperature: float = 0.1
    gemini_max_tokens: int = 8192
    
    # English-focused TTS Voice Options
    available_voices: dict = {
        # Coqui TTS - Highest Quality
        "tts_models/en/ljspeech/tacotron2-DDC": "LJSpeech - High Quality (Recommended)",
        "tts_models/en/vctk/vits": "VCTK Multi-Speaker - Natural",
        "tts_models/en/ljspeech/glow-tts": "GlowTTS - Fast & Clear",
        
        # Edge TTS - Good Fallback
        "en-US-AriaNeural": "Edge - Aria (Natural)",
        "en-US-JennyNeural": "Edge - Jenny (Professional)",
        "en-US-GuyNeural": "Edge - Guy (Deep)",
        "en-GB-SoniaNeural": "Edge - Sonia (British)",
        "en-AU-NatashaNeural": "Edge - Natasha (Australian)",
    }
    
    # Performance Settings
    gpu_enabled: bool = os.getenv("GPU_ENABLED", "True").lower() == "true"
    cpu_threads: int = int(os.getenv("CPU_THREADS", "4"))
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Create directories if they don't exist
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, 'tts_cache'), exist_ok=True)
        
        # Validate API key
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required. Please set it in your .env file.")
    
    def get_best_tts_engine(self) -> tuple:
        """Get the best available TTS engine and voice."""
        try:
            from TTS.api import TTS
            # Coqui TTS is available
            return ("coqui-xtts", "tts_models/en/ljspeech/tacotron2-DDC")
        except ImportError:
            # Fall back to Edge TTS
            return ("edge-tts", "en-US-AriaNeural")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings() 