"""Celery task для автоматического закрытия просроченных отгрузок (запускается по расписанию beat)."""
from app.celery_app import celery_app
from app.core.logging import logger
from app.services.shipment_scheduler import auto_close_expired_shipments_sync


@celery_app.task(bind=True, name="app.tasks.shipment_tasks.auto_close_expired_shipments_task")
def auto_close_expired_shipments_task(self) -> int:
    """Выполнить закрытие просроченных отгрузок в worker (синхронный движок, отдельная сессия)."""
    try:
        count = auto_close_expired_shipments_sync()
        if count > 0:
            logger.info("shipment_beat_run", closed_count=count)
        return count
    except Exception as exc:
        logger.exception("shipment_beat_error", error=str(exc))
        raise
