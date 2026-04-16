"""Celery app for background tasks (e.g. document conversion in isolated worker)."""
import logging

from celery import Celery
from celery.schedules import crontab, schedule

from app.core.config import settings

_redis_dsn = (settings.REDIS_DSN or "").strip()
if not _redis_dsn:
    logging.warning(
        "REDIS_DSN is empty; using localhost fallback. Set REDIS_DSN in production."
    )
broker = _redis_dsn or "redis://localhost:6379/0"
backend = broker

celery_app = Celery(
    "birka",
    broker=broker,
    backend=backend,
    include=[
        "app.tasks.document_tasks",
        "app.tasks.shipment_tasks",
        "app.tasks.session_cleanup",
        "app.tasks.s3_cleanup",
    ],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_time_limit=120,
    task_soft_time_limit=110,
    worker_prefetch_multiplier=1,
    # Retain broker retry on startup when upgrading to Celery 6+
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "auto-close-expired-shipments": {
            "task": "app.tasks.shipment_tasks.auto_close_expired_shipments_task",
            "schedule": schedule(run_every=settings.SHIPMENT_SCHEDULER_INTERVAL_SECONDS),
        },
        "cleanup-expired-sessions": {
            "task": "app.tasks.session_cleanup.cleanup_expired_sessions",
            "schedule": crontab(minute=0),  # каждый час
        },
        "cleanup-orphaned-s3": {
            "task": "app.tasks.s3_cleanup.cleanup_orphaned_s3_objects",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),  # воскресенье 03:00
        },
    },
)
