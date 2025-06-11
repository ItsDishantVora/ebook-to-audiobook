"""
Health check endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.services import TTSService, GeminiService

router = APIRouter()
logger = structlog.get_logger()

@router.get("/")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "audiobook-converter"}

@router.get("/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check including dependencies."""
    
    health_status = {
        "status": "healthy",
        "service": "audiobook-converter",
        "components": {}
    }
    
    # Check database connection
    try:
        await db.execute("SELECT 1")
        health_status["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy", 
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check TTS service
    try:
        tts_service = TTSService()
        if tts_service.is_available():
            health_status["components"]["tts"] = {
                "status": "healthy",
                "voices": len(tts_service.get_available_voices())
            }
        else:
            health_status["components"]["tts"] = {"status": "unavailable"}
    except Exception as e:
        health_status["components"]["tts"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check Gemini AI service
    try:
        gemini_service = GeminiService()
        if gemini_service.is_available():
            health_status["components"]["gemini"] = {"status": "healthy"}
        else:
            health_status["components"]["gemini"] = {"status": "unavailable"}
    except Exception as e:
        health_status["components"]["gemini"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    return health_status

@router.get("/services")
async def services_status():
    """Check status of external services."""
    
    services = {}
    
    # TTS Service
    try:
        tts_service = TTSService()
        services["tts"] = {
            "available": tts_service.is_available(),
            "voices": tts_service.get_available_voices() if tts_service.is_available() else []
        }
    except Exception as e:
        services["tts"] = {"available": False, "error": str(e)}
    
    # Gemini Service
    try:
        gemini_service = GeminiService()
        services["gemini"] = {
            "available": gemini_service.is_available()
        }
    except Exception as e:
        services["gemini"] = {"available": False, "error": str(e)}
    
    return {"services": services} 