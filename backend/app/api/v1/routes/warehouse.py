"""Warehouse endpoints."""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.v1.deps import get_current_user, require_roles
from app.db.models.barcode_scan_log import BarcodeScanLog
from app.db.models.company import Company
from app.db.models.fbo_supply import FBOSupply, FBOSupplyBox
from app.db.models.order import Order, OrderItem
from app.db.models.order_photo import OrderPhoto
from app.db.models.packing_record import PackingRecord
from app.db.models.product import Product
from app.db.models.shipment_request import ShipmentRequest
from app.db.models.warehouse_employee import WarehouseEmployee
from app.db.session import get_db
from app.schemas.warehouse import (
    BarcodeValidateInOrderRequest,
    BarcodeValidateInOrderResponse,
    BarcodeValidateRequest,
    BarcodeValidateResponse,
    PackingRecordCreate,
    ReceivingComplete,
)
from app.services.excel import export_fbo_shipping, parse_fbo_excel
from app.services.files import content_disposition
from app.services.telegram import send_document, send_notification
from app.core.logging import logger
from app.db.models.user import User

router = APIRouter()


@router.post("/receiving/complete")
async def complete_receiving(
    payload: ReceivingComplete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("warehouse", "admin")),
) -> dict:
    """Complete receiving for order."""
    try:
        result = await db.execute(select(Order).where(Order.id == payload.order_id))
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        company_result = await db.execute(select(Company).where(Company.id == order.company_id))
        if not company_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Компания не найдена")

        total_received = 0
        total_defect = 0
        for item in payload.items:
            if item.received_qty < 0 or item.defect_qty < 0 or item.adjustment_qty < 0:
                raise HTTPException(status_code=400, detail="Некорректные количества")
            if item.received_qty < item.defect_qty + item.adjustment_qty:
                raise HTTPException(status_code=400, detail="Полученное количество меньше суммы списаний и брака")
            item_result = await db.execute(
                select(OrderItem).where(
                    OrderItem.id == item.order_item_id,
                    OrderItem.order_id == payload.order_id,
                )
            )
            order_item = item_result.scalar_one_or_none()
            if not order_item:
                raise HTTPException(
                    status_code=400,
                    detail="Товар заявки не найден или не принадлежит этой заявке",
                )
            if item.defect_qty > 0:
                photo_count_result = await db.execute(
                    select(func.count())
                    .select_from(OrderPhoto)
                    .where(
                        OrderPhoto.order_id == payload.order_id,
                        OrderPhoto.product_id == order_item.product_id,
                        OrderPhoto.photo_type == "defect",
                    )
                )
                photo_count = int(photo_count_result.scalar_one())
                if photo_count < item.defect_qty:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Требуется {item.defect_qty} фото брака для товара (product_id={order_item.product_id}), загружено {photo_count}",
                    )
            # Инвариант: received_qty >= defect_qty + adjustment_qty (проверено выше)
            old_net = order_item.received_qty - order_item.defect_qty - (order_item.adjustment_qty or 0)
            new_net = item.received_qty - item.defect_qty - (item.adjustment_qty or 0)
            delta_stock = new_net - old_net
            delta_defect = item.defect_qty - order_item.defect_qty

            order_item.received_qty = item.received_qty
            order_item.defect_qty = item.defect_qty
            order_item.adjustment_qty = item.adjustment_qty
            order_item.adjustment_note = item.adjustment_note
            total_received += item.received_qty
            total_defect += item.defect_qty

            product_result = await db.execute(select(Product).where(Product.id == order_item.product_id))
            product = product_result.scalar_one_or_none()
            if product:
                product.stock_quantity = max(0, product.stock_quantity + delta_stock)
                product.defect_quantity = max(0, product.defect_quantity + delta_defect)

        all_items_result = await db.execute(select(OrderItem).where(OrderItem.order_id == payload.order_id))
        all_order_items = all_items_result.scalars().all()
        all_order_item_ids = {oi.id for oi in all_order_items}
        payload_item_ids = {item.order_item_id for item in payload.items}
        full_submission = all_order_item_ids <= payload_item_ids and len(payload.items) >= len(all_order_items)
        not_received_count = sum(1 for oi in all_order_items if oi.received_qty == 0)

        if full_submission:
            order.received_qty = sum(oi.received_qty for oi in all_order_items)
            order.status = "Принято"
        elif not_received_count > 0:
            await db.commit()
            return {
                "status": "partial",
                "received": total_received,
                "defects": total_defect,
                "remaining": not_received_count,
            }
        else:
            order.received_qty = total_received
            order.status = "Принято"
        company_result = await db.execute(
            select(Company).where(Company.id == order.company_id).options(joinedload(Company.user))
        )
        company = company_result.scalar_one_or_none()
        telegram_id = company.user.telegram_id if company and company.user else None
        order_number = order.order_number
        await db.commit()
        if telegram_id:
            await send_notification(
                telegram_id,
                f"Заявка {order_number} принята на склад.",
            )
        return {"received": total_received, "defects": total_defect}
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("receiving_complete_failed", order_id=payload.order_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Не удалось завершить приёмку")


@router.post("/packing/record")
async def create_packing_record(
    payload: PackingRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("warehouse", "admin")),
) -> dict:
    """Create packing record."""
    try:
        employee_code = payload.employee_code.strip()
        if not employee_code:
            raise HTTPException(status_code=400, detail="Укажите код сотрудника")
        employee_result = await db.execute(
            select(WarehouseEmployee).where(WarehouseEmployee.employee_code == employee_code)
        )
        employee = employee_result.scalar_one_or_none()
        if not employee:
            employee = WarehouseEmployee(user_id=current_user.id, employee_code=employee_code)
            db.add(employee)
            await db.flush()
            logger.info(
                "warehouse_employee_auto_created",
                user_id=current_user.id,
                employee_code=employee_code,
            )

        order_result = await db.execute(select(Order).where(Order.id == payload.order_id))
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        # Разрешить упаковку, если приёмка завершена (статус уже после приёмки) или есть принятое кол-во
        reception_done = order.status in ("Принято", "Упаковка", "Готово к отгрузке", "Завершено") or order.received_qty > 0
        if not reception_done:
            raise HTTPException(
                status_code=400,
                detail="Упаковка возможна только после завершения приёмки заявки.",
            )
        company_result = await db.execute(select(Company).where(Company.id == order.company_id))
        if not company_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Компания не найдена")

        order_item_result = await db.execute(
            select(OrderItem).where(
                OrderItem.id == payload.order_item_id,
                OrderItem.order_id == payload.order_id,
                OrderItem.product_id == payload.product_id,
            )
        )
        order_item = order_item_result.scalar_one_or_none()
        if not order_item:
            raise HTTPException(
                status_code=400,
                detail="Товар заявки не найден или не совпадает с заказом и товаром.",
            )
        remainder = order_item.received_qty - order_item.packed_qty
        if payload.quantity > remainder:
            raise HTTPException(
                status_code=400,
                detail=f"Перепаковка: по позиции доступно к упаковке {remainder} шт., указано {payload.quantity}.",
            )

        items_result = await db.execute(select(OrderItem).where(OrderItem.order_id == payload.order_id))
        order_items_list = items_result.scalars().all()
        total_defect = sum(i.defect_qty for i in order_items_list)
        effective_plan = order.received_qty - total_defect
        if payload.quantity > 0 and (order_item.received_qty - order_item.defect_qty - order_item.packed_qty) < payload.quantity:
            logger.warning(
                "packing_exceeds_effective_plan",
                order_id=payload.order_id,
                order_item_id=payload.order_item_id,
                received=order_item.received_qty,
                defect=order_item.defect_qty,
                packed_before=order_item.packed_qty,
                packed_now=payload.quantity,
            )

        record = PackingRecord(
            order_id=payload.order_id,
            order_item_id=payload.order_item_id,
            product_id=payload.product_id,
            employee_id=employee.id,
            pallet_number=payload.pallet_number,
            box_number=payload.box_number,
            quantity=payload.quantity,
            warehouse=payload.warehouse,
            box_barcode=payload.box_barcode,
            materials_used=payload.materials_used,
            time_spent_minutes=payload.time_spent_minutes,
        )
        db.add(record)

        order.packed_qty += payload.quantity
        order_item.packed_qty += payload.quantity

        if order.packed_qty >= order.received_qty:
            order.status = "Готово к отгрузке"
        else:
            order.status = "Упаковка"

        product_result = await db.execute(select(Product).where(Product.id == payload.product_id))
        product = product_result.scalar_one_or_none()
        if product:
            product.stock_quantity = max(product.stock_quantity - payload.quantity, 0)

        await db.commit()
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("packing_record_failed", order_id=payload.order_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Не удалось сохранить запись упаковки")


@router.post("/barcode/validate", response_model=BarcodeValidateResponse)
async def validate_barcode(
    payload: BarcodeValidateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("warehouse", "admin")),
) -> BarcodeValidateResponse:
    """Validate barcode against products or FBO box barcodes. Each call is logged to barcode_scan_log."""
    try:
        barcode = (payload.barcode or "").strip()
        result = await db.execute(select(Product).where(Product.barcode == barcode))
        product = result.scalar_one_or_none()
        if product:
            company_result = await db.execute(select(Company).where(Company.id == product.company_id))
            if not company_result.scalar_one_or_none():
                return BarcodeValidateResponse(valid=False, message="ШК не найден")
            logger.info("barcode_validate_ok", product_id=product.id, barcode_len=len(barcode))
            response = BarcodeValidateResponse(
                valid=True,
                message=f"ШК найден: {product.name}",
                type="product",
                product={
                    "id": product.id,
                    "name": product.name,
                    "brand": product.brand,
                    "size": product.size,
                    "color": product.color,
                    "wb_article": product.wb_article,
                    "barcode": product.barcode,
                },
            )
            log_company_id = product.company_id
            log_valid = True
            log_result_type = "product"
            log_product_id = product.id
            log_fbo_supply_box_id = None
        else:
            box_result = await db.execute(
                select(FBOSupplyBox).where(FBOSupplyBox.external_barcode == barcode)
            )
            box = box_result.scalar_one_or_none()
            if box:
                logger.info("barcode_validate_box_ok", box_id=box.id, supply_id=box.supply_id)
                supply_result = await db.execute(
                    select(FBOSupply).where(FBOSupply.id == box.supply_id)
                )
                supply = supply_result.scalar_one_or_none()
                log_company_id = supply.company_id if supply else payload.company_id
                response = BarcodeValidateResponse(
                    valid=True,
                    message=f"Короб №{box.box_number}",
                    type="box",
                    box={
                        "id": box.id,
                        "box_number": box.box_number,
                        "supply_id": box.supply_id,
                        "external_box_id": box.external_box_id,
                        "external_barcode": box.external_barcode,
                    },
                )
                log_valid = True
                log_result_type = "box"
                log_product_id = None
                log_fbo_supply_box_id = box.id
            else:
                response = BarcodeValidateResponse(valid=False, message="ШК не найден")
                log_company_id = payload.company_id
                log_valid = False
                log_result_type = None
                log_product_id = None
                log_fbo_supply_box_id = None

        try:
            scan_log = BarcodeScanLog(
                user_id=current_user.id,
                company_id=log_company_id,
                barcode=barcode,
                order_id=payload.order_id,
                scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
                valid=log_valid,
                result_type=log_result_type,
                product_id=log_product_id,
                fbo_supply_box_id=log_fbo_supply_box_id,
            )
            db.add(scan_log)
            await db.commit()
        except Exception as log_exc:
            logger.exception("barcode_scan_log_insert_failed", error=str(log_exc))

        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("barcode_validate_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Ошибка проверки штрихкода")


@router.post("/barcode/validate-in-order", response_model=BarcodeValidateInOrderResponse)
async def validate_barcode_in_order(
    payload: BarcodeValidateInOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("warehouse", "admin")),
) -> BarcodeValidateInOrderResponse:
    """Validate barcode in order context: find order item by barcode, return remaining qty."""
    try:
        barcode = (payload.barcode or "").strip()
        order_result = await db.execute(select(Order).where(Order.id == payload.order_id))
        order = order_result.scalar_one_or_none()
        if not order:
            return BarcodeValidateInOrderResponse(found=False, message="Заявка не найдена")
        company_result = await db.execute(select(Company).where(Company.id == order.company_id))
        if not company_result.scalar_one_or_none():
            return BarcodeValidateInOrderResponse(found=False, message="Заявка не найдена")
        result = await db.execute(
            select(OrderItem, Product)
            .join(Product, Product.id == OrderItem.product_id)
            .where(OrderItem.order_id == payload.order_id, Product.barcode == barcode)
        )
        row = result.first()
        if not row:
            return BarcodeValidateInOrderResponse(
                found=False,
                message="ШК не относится к выбранной заявке",
            )
        item, product = row
        remaining_to_receive = max(0, item.planned_qty - item.received_qty)
        remaining_to_pack = max(0, item.received_qty - item.defect_qty - item.packed_qty)
        logger.info(
            "barcode_validate_in_order_ok",
            order_id=payload.order_id,
            order_item_id=item.id,
        )
        return BarcodeValidateInOrderResponse(
            found=True,
            message=f"Товар в заявке: {product.name}, план {item.planned_qty}, принято {item.received_qty}",
            order_item={
                "id": item.id,
                "product_id": item.product_id,
                "product_name": product.name,
                "planned_qty": item.planned_qty,
                "received_qty": item.received_qty,
                "packed_qty": item.packed_qty,
                "defect_qty": item.defect_qty,
            },
            remaining_to_receive=remaining_to_receive,
            remaining_to_pack=remaining_to_pack,
        )
    except Exception as exc:
        logger.exception("barcode_validate_in_order_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Ошибка проверки штрихкода в заявке")


@router.post("/order/{order_id}/complete")
async def complete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("warehouse", "admin")),
) -> dict:
    """Mark order as completed (warehouse/admin)."""
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    company_result = await db.execute(
        select(Company).where(Company.id == order.company_id).options(joinedload(Company.user))
    )
    company = company_result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    telegram_id = company.user.telegram_id if company.user else None
    order_number = order.order_number
    packed_qty_val = order.packed_qty
    order.status = "Завершено"
    order.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    if telegram_id:
        msg = f"Заявка {order_number}: Завершено. Упаковано всего {packed_qty_val} шт."
        await send_notification(telegram_id, msg)
    return {"status": "ok"}


@router.get("/export-fbo")
async def export_fbo_excel(
    order_id: int = Query(..., description="Order ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("warehouse", "admin")),
) -> StreamingResponse:
    """Export FBO shipping (packing records) for order to Excel."""
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    company_result = await db.execute(select(Company).where(Company.id == order.company_id))
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    result = await db.execute(
        select(PackingRecord)
        .options(
            joinedload(PackingRecord.product),
            joinedload(PackingRecord.employee),
        )
        .where(PackingRecord.order_id == order_id)
    )
    records = list(result.unique().scalars().all())
    if not records:
        raise HTTPException(status_code=400, detail="Нет записей упаковки для выгрузки")
    sr_result = await db.execute(
        select(ShipmentRequest).where(ShipmentRequest.order_id == order_id).limit(1)
    )
    sr = sr_result.scalar_one_or_none()
    delivery_date_str = sr.delivery_date.isoformat() if sr and sr.delivery_date else None
    buffer = export_fbo_shipping(records, delivery_date_str)
    filename = f"Отгрузка_FBO_заявка_{order.order_number}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": content_disposition(filename)},
    )


@router.post("/export-fbo/send")
async def send_export_fbo_to_telegram(
    order_id: int = Query(..., description="Order ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("warehouse", "admin")),
) -> dict:
    """Export FBO and send to current user (who clicked) in Telegram."""
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    telegram_id = getattr(current_user, "telegram_id", None)
    if not telegram_id:
        raise HTTPException(status_code=400, detail="Telegram не привязан к вашему аккаунту")
    result = await db.execute(
        select(PackingRecord)
        .options(
            joinedload(PackingRecord.product),
            joinedload(PackingRecord.employee),
        )
        .where(PackingRecord.order_id == order_id)
    )
    records = list(result.unique().scalars().all())
    if not records:
        raise HTTPException(status_code=400, detail="Нет записей упаковки для выгрузки")
    sr_result = await db.execute(
        select(ShipmentRequest).where(ShipmentRequest.order_id == order_id).limit(1)
    )
    sr = sr_result.scalar_one_or_none()
    delivery_date_str = sr.delivery_date.isoformat() if sr and sr.delivery_date else None
    buffer = export_fbo_shipping(records, delivery_date_str)
    file_bytes = buffer.getvalue()
    filename = f"Отгрузка_FBO_заявка_{order.order_number}.xlsx"
    sent = await send_document(telegram_id, file_bytes, filename, caption="Отгрузка FBO")
    if not sent:
        raise HTTPException(status_code=502, detail="Не удалось отправить файл в Telegram. Попробуйте позже.")
    return {"sent": True}


@router.post("/orders/{order_id}/import-fbo")
async def import_fbo_excel(
    order_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Import FBO Excel (packing_id + Баркод короба) and update packing records for this order."""
    if not file.filename or not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="Загрузите файл Excel (.xlsx или .xls)")
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if current_user.role not in ("warehouse", "admin"):
        company_result = await db.execute(
            select(Company).where(Company.id == order.company_id, Company.user_id == current_user.id)
        )
        if not company_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Заявка не найдена")
    data = await file.read()
    try:
        rows = parse_fbo_excel(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not rows:
        raise HTTPException(status_code=400, detail="В файле нет строк с packing_id")
    updated = 0
    new_delivery_date_str = None

    for row in rows:
        if row.get("delivery_date") and not new_delivery_date_str:
            new_delivery_date_str = row["delivery_date"]

        rec_result = await db.execute(
            select(PackingRecord).where(
                PackingRecord.id == row["packing_id"],
                PackingRecord.order_id == order_id,
            )
        )
        rec = rec_result.scalar_one_or_none()
        if rec:
            has_update = False
            if row.get("box_barcode") is not None:
                rec.box_barcode = row["box_barcode"]
                has_update = True
            if row.get("warehouse") is not None:
                rec.warehouse = row["warehouse"]
                has_update = True
            if has_update:
                updated += 1

    if new_delivery_date_str:
        try:
            parsed_date: date | None = None
            if len(new_delivery_date_str) >= 10:
                try:
                    parsed_date = datetime.strptime(new_delivery_date_str[:10], "%Y-%m-%d").date()
                except ValueError:
                    try:
                        parsed_date = datetime.strptime(new_delivery_date_str[:10], "%d.%m.%Y").date()
                    except ValueError:
                        pass
            if parsed_date:
                sr_result = await db.execute(
                    select(ShipmentRequest).where(ShipmentRequest.order_id == order_id).limit(1)
                )
                sr = sr_result.scalar_one_or_none()
                if sr:
                    sr.delivery_date = parsed_date
        except Exception as e:
            logger.warning(
                "failed_to_parse_imported_delivery_date",
                date_str=new_delivery_date_str,
                error=str(e),
            )

    await db.commit()
    return {"updated": updated}
