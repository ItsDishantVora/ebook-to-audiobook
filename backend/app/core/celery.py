"""
Celery configuration for the AudioBook Converter application.
"""

import os
from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery("audiobook_converter")

# Configure Celery
celery_app.conf.update(
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    include=['app.tasks.conversion_tasks']
)

# Auto-discover tasks from all installed apps
celery_app.autodiscover_tasks(['app.tasks.conversion_tasks'])

# Task routes (optional, for organizing tasks)
celery_app.conf.task_routes = {
    'app.services.conversion_service.*': {'queue': 'conversion'},
    'app.services.tts_service.*': {'queue': 'tts'},
}

# Configure task result backend settings
celery_app.conf.result_expires = 3600  # 1 hour

if __name__ == "__main__":
    celery_app.start() 