"""Celery app for background tasks (e.g. document conversion in isolated worker)."""
from celery import Celery
from celery.schedules import schedule

from app.core.config import settings

broker = (settings.REDIS_DSN or "redis://localhost:6379/0").strip()
backend = broker

celery_app = Celery(
    "birka",
    broker=broker,
    backend=backend,
    include=["app.tasks.document_tasks", "app.tasks.shipment_tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_time_limit=120,
    task_soft_time_limit=110,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "auto-close-expired-shipments": {
            "task": "app.tasks.shipment_tasks.auto_close_expired_shipments_task",
            "schedule": schedule(run_every=settings.SHIPMENT_SCHEDULER_INTERVAL_SECONDS),
        },
    },
)
