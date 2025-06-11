"""
Main API router that includes all route modules.
"""
from fastapi import APIRouter

from app.api.endpoints import books, conversion, users, health

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(books.router, prefix="/books", tags=["books"])
api_router.include_router(conversion.router, prefix="/conversion", tags=["conversion"]) 