"""
Database connection and session management.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from typing import AsyncGenerator
from contextlib import contextmanager
import structlog

from .config import settings

logger = structlog.get_logger()

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for all models
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Database session error", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()

# Create synchronous engine for Celery tasks
sync_database_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
sync_engine = create_engine(sync_database_url, pool_pre_ping=True, pool_recycle=300)

# Create synchronous session maker for Celery tasks
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

@contextmanager
def get_db_session():
    """
    Context manager for synchronous database sessions (for Celery tasks).
    """
    session = SyncSessionLocal()
    try:
        yield session
    except Exception as e:
        logger.error("Sync database session error", error=str(e))
        session.rollback()
        raise
    finally:
        session.close()

async def init_db() -> None:
    """
    Initialize database tables.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully") 