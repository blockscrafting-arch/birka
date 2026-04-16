"""Periodic cleanup of expired sessions."""

from celery import shared_task
from sqlalchemy import delete, text

from app.core.logging import logger
from app.db.models.session import Session
from app.db.session import SyncSessionLocal


@shared_task(
    name="app.tasks.session_cleanup.cleanup_expired_sessions",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def cleanup_expired_sessions() -> int:
    """Delete sessions past their expires_at."""
    with SyncSessionLocal() as db:
        result = db.execute(delete(Session).where(Session.expires_at < text("NOW()")))
        db.commit()
        count = result.rowcount
        if count:
            logger.info("sessions_cleaned", deleted=count)
        return count
