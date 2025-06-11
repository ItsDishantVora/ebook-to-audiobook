"""
Simple test task for Celery verification.
"""
from celery import Celery
import os

# Create Celery app instance
celery_app = Celery('audiobook_converter')

# Configure with Redis
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
celery_app.conf.update(
    broker_url=redis_url,
    result_backend=redis_url,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@celery_app.task
def test_task(message="Hello World"):
    """Simple test task."""
    return f"Test task completed: {message}"

@celery_app.task  
def convert_book_to_audiobook(book_id: str, job_id: str, voice: str = "default", speed: str = "normal"):
    """
    Simple version of the conversion task for testing.
    """
    import time
    time.sleep(2)  # Simulate some work
    return {
        "book_id": book_id,
        "job_id": job_id,
        "status": "completed",
        "message": "Test conversion completed"
    } 