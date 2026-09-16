"""Celery application for background processing.

Document parsing, chunking, and embedding involve slow I/O (disk reads,
OpenAI calls) that shouldn't block an HTTP request/response cycle. Using a
real task queue — instead of FastAPI's in-process BackgroundTasks — means
jobs survive an API process restart, get automatic retries, and can be
scaled independently by adding more worker containers.

Run a worker with:
    celery -A worker.celery_app worker --loglevel=info
"""

from celery import Celery

from config import get_settings

settings = get_settings()

celery_app = Celery(
    "meridian",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,          # Re-queue a task if the worker dies mid-job
    worker_prefetch_multiplier=1,  # Fair dispatch for long-running jobs
    task_default_retry_delay=10,
    task_time_limit=300,          # Hard kill after 5 minutes
    task_soft_time_limit=270,
)

celery_app.autodiscover_tasks(["worker"])
