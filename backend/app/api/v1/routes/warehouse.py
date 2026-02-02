"""Warehouse endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.v1.deps import get_current_user, require_roles
from app.db.models.company import Company
from app.db.models.order import Order, OrderItem
from app.db.models.packing_record import PackingRecord
from app.db.models.product import Product
from app.db.models.warehouse_employee import WarehouseEmployee
from app.db.session import get_db
from app.schemas.warehouse import BarcodeValidateRequest, PackingRecordCreate, ReceivingComplete
from app.services.excel import export_fbo_shipping
from app.services.files import content_disposition
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
            raise HTTPException(status_code=404, detail="Order not found")
        company_result = await db.execute(select(Company).where(Company.id == order.company_id))
        if not company_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Company not found")

        total_received = 0
        total_defect = 0
        for item in payload.items:
            if item.received_qty < 0 or item.defect_qty < 0 or item.adjustment_qty < 0:
                raise HTTPException(status_code=400, detail="Invalid quantities")
            if item.received_qty < item.defect_qty + item.adjustment_qty:
                raise HTTPException(status_code=400, detail="Received quantity is меньше списаний/брака")
            item_result = await db.execute(select(OrderItem).where(OrderItem.id == item.order_item_id))
            order_item = item_result.scalar_one_or_none()
            if not order_item:
                continue
            order_item.received_qty = item.received_qty
            order_item.defect_qty = item.defect_qty
            order_item.adjustment_qty = item.adjustment_qty
            order_item.adjustment_note = item.adjustment_note
            total_received += item.received_qty
            total_defect += item.defect_qty

            product_result = await db.execute(select(Product).where(Product.id == order_item.product_id))
            product = product_result.scalar_one_or_none()
            if product:
                net_received = item.received_qty - item.defect_qty - item.adjustment_qty
                product.stock_quantity += max(net_received, 0)
                product.defect_quantity += item.defect_qty

        order.received_qty = total_received
        order.status = "Принято"
        await db.commit()
        return {"received": total_received, "defects": total_defect}
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("receiving_complete_failed", order_id=payload.order_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Receiving completion failed")


@router.post("/packing/record")
async def create_packing_record(
    payload: PackingRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("warehouse", "admin")),
) -> dict:
    """Create packing record."""
    try:
        employee_result = await db.execute(
            select(WarehouseEmployee).where(WarehouseEmployee.employee_code == payload.employee_code)
        )
        employee = employee_result.scalar_one_or_none()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

        order_result = await db.execute(select(Order).where(Order.id == payload.order_id))
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        company_result = await db.execute(select(Company).where(Company.id == order.company_id))
        if not company_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Company not found")

        record = PackingRecord(
            order_id=payload.order_id,
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
        order.status = "Готово к отгрузке"

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
        raise HTTPException(status_code=500, detail="Packing record failed")


@router.post("/barcode/validate")
async def validate_barcode(
    payload: BarcodeValidateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("warehouse", "admin")),
) -> dict:
    """Validate barcode against products."""
    try:
        result = await db.execute(select(Product).where(Product.barcode == payload.barcode))
        product = result.scalar_one_or_none()
        if not product:
            return {"valid": False, "message": "ШК не найден"}
        company_result = await db.execute(select(Company).where(Company.id == product.company_id))
        if not company_result.scalar_one_or_none():
            return {"valid": False, "message": "ШК не найден"}
        return {
            "valid": True,
            "message": f"ШК найден: {product.name}",
            "product": {
                "id": product.id,
                "name": product.name,
                "brand": product.brand,
                "size": product.size,
                "color": product.color,
                "wb_article": product.wb_article,
                "barcode": product.barcode,
            },
        }
    except Exception as exc:
        logger.exception("barcode_validate_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Barcode validation failed")


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
        raise HTTPException(status_code=404, detail="Order not found")
    company_result = await db.execute(select(Company).where(Company.id == order.company_id))
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")
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
        raise HTTPException(status_code=400, detail="No packing records to export")
    buffer = export_fbo_shipping(records)
    filename = f"Отгрузка_FBO_заявка_{order.order_number}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": content_disposition(filename)},
    )
