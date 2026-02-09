"""Celery app for background tasks (e.g. document conversion in isolated worker)."""
from celery import Celery

from app.core.config import settings

broker = (settings.REDIS_DSN or "redis://localhost:6379/0").strip()
backend = broker

celery_app = Celery(
    "birka",
    broker=broker,
    backend=backend,
    include=["app.tasks.document_tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_time_limit=120,
    task_soft_time_limit=110,
    worker_prefetch_multiplier=1,
)
