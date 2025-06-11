"""
Book conversion endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog

from app.core.database import get_db
from app.models import Book, ConversionJob, JobType, JobStatus, BookStatus
from app.core.celery import celery_app

router = APIRouter()
logger = structlog.get_logger()

@router.post("/{book_id}/start")
async def start_conversion(
    book_id: str,
    voice: Optional[str] = "default",
    speed: Optional[str] = "normal",
    db: AsyncSession = Depends(get_db)
):
    """Start the full conversion process for a book."""
    try:
        # Check if book exists
        result = await db.execute(select(Book).where(Book.id == book_id))
        book = result.scalar_one_or_none()
        
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        if book.is_processing:
            raise HTTPException(
                status_code=400, 
                detail=f"Book is already being processed. Current status: {book.status.value}"
            )
        
        if book.has_failed:
            # Reset book status for retry
            book.status = BookStatus.UPLOADED
            book.error_message = None
        
        # Create conversion job
        job = ConversionJob(
            job_type=JobType.FULL_CONVERSION,
            status=JobStatus.PENDING,
            book_id=book.id,
            user_id=book.user_id,
            parameters={
                "voice": voice,
                "speed": speed
            }
        )
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # Start Celery task
        task = celery_app.send_task(
            'app.tasks.conversion_tasks.convert_book_to_audiobook',
            args=[str(book.id), str(job.id)],
            kwargs={"voice": voice, "speed": speed}
        )
        
        # Update job with Celery task ID
        job.celery_task_id = task.id
        job.status = JobStatus.STARTED
        await db.commit()
        
        logger.info("Conversion started", book_id=book_id, job_id=str(job.id), task_id=task.id)
        
        return {
            "message": "Conversion started",
            "job_id": str(job.id),
            "task_id": task.id,
            "book_id": book_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start conversion", book_id=book_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start conversion")

@router.get("/{job_id}/status")
async def get_conversion_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the status of a conversion job."""
    try:
        result = await db.execute(select(ConversionJob).where(ConversionJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Conversion job not found")
        
        # Get additional info from Celery if job is running
        celery_info = None
        if job.celery_task_id and job.is_running:
            try:
                celery_result = celery_app.AsyncResult(job.celery_task_id)
                celery_info = {
                    "celery_status": celery_result.status,
                    "celery_info": celery_result.info if celery_result.info else {}
                }
            except Exception as e:
                logger.warning("Failed to get Celery task info", task_id=job.celery_task_id, error=str(e))
        
        response = {
            "job_id": str(job.id),
            "book_id": str(job.book_id),
            "status": job.status.value,
            "progress_percentage": job.progress_percentage,
            "current_step": job.current_step,
            "created_at": job.created_at.isoformat(),
            "estimated_duration_seconds": job.estimated_duration_seconds,
            "error_message": job.error_message
        }
        
        if job.started_at:
            response["started_at"] = job.started_at.isoformat()
        
        if job.completed_at:
            response["completed_at"] = job.completed_at.isoformat()
            response["actual_duration_seconds"] = job.actual_duration_seconds
        
        if celery_info:
            response["celery"] = celery_info
        
        # Calculate ETA if job is running
        if job.is_running:
            eta = job.get_eta_seconds()
            if eta:
                response["eta_seconds"] = eta
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get conversion status", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get conversion status")

@router.delete("/{job_id}/cancel")
async def cancel_conversion(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a running conversion job."""
    try:
        result = await db.execute(select(ConversionJob).where(ConversionJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Conversion job not found")
        
        if not job.is_running:
            raise HTTPException(
                status_code=400, 
                detail=f"Job is not running. Current status: {job.status.value}"
            )
        
        # Cancel Celery task
        if job.celery_task_id:
            celery_app.control.revoke(job.celery_task_id, terminate=True)
        
        # Update job status
        job.status = JobStatus.REVOKED
        job.completed_at = func.now()
        await db.commit()
        
        logger.info("Conversion cancelled", job_id=job_id, task_id=job.celery_task_id)
        
        return {"message": "Conversion cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel conversion", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to cancel conversion")

@router.get("/")
async def get_conversions(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get list of conversion jobs."""
    try:
        query = select(ConversionJob).offset(skip).limit(limit).order_by(ConversionJob.created_at.desc())
        
        if status:
            try:
                status_enum = JobStatus(status)
                query = query.where(ConversionJob.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        result = await db.execute(query)
        jobs = result.scalars().all()
        
        return {
            "conversions": [
                {
                    "id": str(job.id),
                    "book_id": str(job.book_id),
                    "job_type": job.job_type.value,
                    "status": job.status.value,
                    "progress_percentage": job.progress_percentage,
                    "current_step": job.current_step,
                    "created_at": job.created_at.isoformat(),
                    "error_message": job.error_message
                }
                for job in jobs
            ],
            "total": len(jobs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get conversions", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve conversions") 