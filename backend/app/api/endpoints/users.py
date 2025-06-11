"""
User management endpoints.
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_users():
    """Get users - placeholder endpoint."""
    return {"users": [], "message": "Users endpoint - coming soon"} 