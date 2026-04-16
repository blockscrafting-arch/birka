"""Фоновая задача: автоматическая смена статуса отгрузок по дате поставки."""
import asyncio
from datetime import date, datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.logging import logger
from app.db.models.company import Company
from app.db.models.order import Order
from app.db.models.shipment_request import ShipmentRequest
from app.db.session import AsyncSessionLocal, SyncSessionLocal
from app.services.telegram import send_notification, send_notification_sync

SHIPPED_STATUS = "Отгружено"
ORDER_COMPLETED_STATUS = "Завершено"


async def auto_close_expired_shipments() -> int:
    """Перевести в 'Отгружено' все ShipmentRequest с delivery_date <= сегодня и статусом != 'Отгружено'.

    Для каждой такой отгрузки также обновляет связанный Order: status = 'Завершено', completed_at = now,
    если заказ ещё не завершён.

    Returns:
        Количество обновлённых заявок на отгрузку.
    """
    today = date.today()
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ShipmentRequest).where(
                ShipmentRequest.delivery_date.isnot(None),
                ShipmentRequest.delivery_date <= today,
                ShipmentRequest.status != SHIPPED_STATUS,
            )
        )
        requests = list(result.scalars().all())
        if not requests:
            return 0

        order_ids_to_complete: set[int] = set()
        for req in requests:
            req.status = SHIPPED_STATUS
            if req.order_id is not None:
                order_ids_to_complete.add(req.order_id)
            logger.info(
                "shipment_auto_closed",
                shipment_request_id=req.id,
                delivery_date=str(req.delivery_date),
            )

        if order_ids_to_complete:
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.execute(
                update(Order).where(
                    Order.id.in_(order_ids_to_complete),
                    Order.status != ORDER_COMPLETED_STATUS,
                ).values(
                    status=ORDER_COMPLETED_STATUS,
                    completed_at=now_utc,
                    updated_at=now_utc,
                )
            )
            for oid in order_ids_to_complete:
                logger.info("order_auto_completed_by_shipment", order_id=oid)

        await db.commit()

        # Уведомить клиентов о завершении заказа по дате отгрузки (без ПДн в логах)
        if order_ids_to_complete:
            orders_result = await db.execute(
                select(Order)
                .where(Order.id.in_(order_ids_to_complete))
                .options(joinedload(Order.company).joinedload(Company.user))
            )
            for order in orders_result.unique().scalars().all():
                if order.company and order.company.user and order.company.user.telegram_id:
                    msg = (
                        f"Заявка {order.order_number}: Завершено (автоматически по дате отгрузки). "
                        f"Упаковано всего {order.packed_qty} шт."
                    )
                    try:
                        await send_notification(order.company.user.telegram_id, msg)
                    except Exception as exc:
                        logger.warning(
                            "shipment_auto_complete_notification_failed",
                            order_id=order.id,
                            error=str(exc),
                        )

        return len(requests)


def auto_close_expired_shipments_sync() -> int:
    """Синхронная версия для Celery: закрыть просроченные отгрузки через psycopg2.

    Отдельная сессия на каждый вызов, без async — избегает asyncpg «another operation in progress».
    """
    today = date.today()
    with SyncSessionLocal() as db:
        result = db.execute(
            select(ShipmentRequest).where(
                ShipmentRequest.delivery_date.isnot(None),
                ShipmentRequest.delivery_date <= today,
                ShipmentRequest.status != SHIPPED_STATUS,
            )
        )
        requests = list(result.scalars().all())
        if not requests:
            return 0

        order_ids_to_complete: set[int] = set()
        for req in requests:
            req.status = SHIPPED_STATUS
            if req.order_id is not None:
                order_ids_to_complete.add(req.order_id)
            logger.info(
                "shipment_auto_closed",
                shipment_request_id=req.id,
                delivery_date=str(req.delivery_date),
            )

        if order_ids_to_complete:
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            db.execute(
                update(Order).where(
                    Order.id.in_(order_ids_to_complete),
                    Order.status != ORDER_COMPLETED_STATUS,
                ).values(
                    status=ORDER_COMPLETED_STATUS,
                    completed_at=now_utc,
                    updated_at=now_utc,
                )
            )
            for oid in order_ids_to_complete:
                logger.info("order_auto_completed_by_shipment", order_id=oid)

        db.commit()

        if order_ids_to_complete:
            orders_result = db.execute(
                select(Order)
                .where(Order.id.in_(order_ids_to_complete))
                .options(joinedload(Order.company).joinedload(Company.user))
            )
            for order in orders_result.unique().scalars().all():
                if order.company and order.company.user and order.company.user.telegram_id:
                    msg = (
                        f"Заявка {order.order_number}: Завершено (автоматически по дате отгрузки). "
                        f"Упаковано всего {order.packed_qty} шт."
                    )
                    try:
                        send_notification_sync(order.company.user.telegram_id, msg)
                    except Exception as exc:
                        logger.warning(
                            "shipment_auto_complete_notification_failed",
                            order_id=order.id,
                            error=str(exc),
                        )

        return len(requests)


SCHEDULER_LOCK_KEY = "birka:scheduler:shipment"
SCHEDULER_LOCK_TTL = 900  # 15 min; if worker dies lock is released


async def _try_acquire_scheduler_lock() -> bool:
    """Try to acquire single-instance lock via Redis. Returns True if we got it."""
    if not (settings.REDIS_DSN and settings.REDIS_DSN.strip()):
        return True
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.REDIS_DSN.strip(), decode_responses=True)
        acquired = await r.set(SCHEDULER_LOCK_KEY, "1", nx=True, ex=SCHEDULER_LOCK_TTL)
        await r.aclose()
        return bool(acquired)
    except Exception as e:
        logger.warning("shipment_scheduler_lock_failed", error=str(e))
        return False


async def _release_scheduler_lock() -> None:
    """Release the scheduler lock so next run can acquire."""
    if not (settings.REDIS_DSN and settings.REDIS_DSN.strip()):
        return
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.REDIS_DSN.strip(), decode_responses=True)
        await r.delete(SCHEDULER_LOCK_KEY)
        await r.aclose()
    except Exception as e:
        logger.warning("shipment_scheduler_lock_release_failed", error=str(e))


async def run_shipment_scheduler(interval_seconds: int = 600) -> None:
    """Запускать auto_close_expired_shipments каждые interval_seconds секунд.

    При наличии REDIS_DSN только один инстанс (из нескольких воркеров) выполняет задачу.
    Не прерывает цикл при исключениях — логирует и продолжает.
    """
    logger.info("shipment_scheduler_started", interval_seconds=interval_seconds)
    while True:
        try:
            if not await _try_acquire_scheduler_lock():
                await asyncio.sleep(interval_seconds)
                continue
            try:
                count = await auto_close_expired_shipments()
                if count > 0:
                    logger.info("shipment_scheduler_run", closed_count=count)
            finally:
                await _release_scheduler_lock()
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("shipment_scheduler_stopped")
            raise
        except Exception as exc:
            logger.exception("shipment_scheduler_error", error=str(exc))
