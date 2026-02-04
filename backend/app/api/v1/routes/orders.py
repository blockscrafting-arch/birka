"""Order endpoints."""
from datetime import date, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.v1.deps import get_current_user
from app.db.models.company import Company
from app.db.models.order import Order, OrderItem
from app.db.models.order_counter import OrderCounter
from app.db.models.order_service import OrderService
from app.db.models.service import Service
from app.db.models.order_photo import OrderPhoto
from app.db.models.product import Product
from app.db.session import get_db
from app.schemas.order import OrderCreate, OrderItemOut, OrderList, OrderOut, OrderPhotoOut, OrderStatusUpdate
from app.services.excel import export_receiving
from app.services.files import content_disposition
from app.services.s3 import S3Service
from app.services.telegram import send_notification
from app.core.config import settings
from app.core.logging import logger
from app.db.models.user import User

router = APIRouter()


@router.post("", response_model=OrderOut)
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderOut:
    """Create order with items."""
    company_result = await db.execute(
        select(Company).where(Company.id == payload.company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")

    if not payload.items:
        raise HTTPException(status_code=400, detail="Order must have at least one item")
    if any(item.planned_qty <= 0 for item in payload.items):
        raise HTTPException(status_code=400, detail="Планируемое количество должно быть больше нуля")

    product_ids = [item.product_id for item in payload.items]
    if len(set(product_ids)) != len(product_ids):
        raise HTTPException(status_code=400, detail="Duplicate products in order")

    products_result = await db.execute(
        select(Product.id).where(Product.company_id == payload.company_id, Product.id.in_(product_ids))
    )
    existing_product_ids = {row[0] for row in products_result.all()}
    if existing_product_ids != set(product_ids):
        raise HTTPException(status_code=400, detail="Один или несколько товаров не найдены")

    services_by_id = {}
    if payload.services:
        if any(s.quantity <= 0 for s in payload.services):
            raise HTTPException(status_code=400, detail="Количество услуги должно быть больше нуля")
        svc_ids = [s.service_id for s in payload.services]
        svc_result = await db.execute(
            select(Service).where(Service.id.in_(svc_ids), Service.is_active.is_(True))
        )
        services_by_id = {s.id: s for s in svc_result.scalars().all()}
        if len(services_by_id) != len(svc_ids):
            raise HTTPException(status_code=400, detail="Одна или несколько услуг не найдены или неактивны")

    try:
        today = date.today()
        prefix = datetime.utcnow().strftime("Заявка %d/%m/%y")
        total_planned = sum(item.planned_qty for item in payload.items)
        transaction = db.begin_nested() if db.in_transaction() else db.begin()
        async with transaction:
            counter_result = await db.execute(
                select(OrderCounter).where(OrderCounter.counter_date == today).with_for_update()
            )
            counter = counter_result.scalar_one_or_none()
            if not counter:
                counter = OrderCounter(counter_date=today, value=0)
                db.add(counter)
                await db.flush()
            counter.value += 1
            order_number = f"{prefix} №{counter.value}"

            order = Order(
                company_id=payload.company_id,
                order_number=order_number,
                status="На приемке",
                destination=payload.destination,
                planned_qty=total_planned,
            )
            db.add(order)
            await db.flush()

            for item in payload.items:
                db.add(
                    OrderItem(
                        order_id=order.id,
                        product_id=item.product_id,
                        planned_qty=item.planned_qty,
                    )
                )

            for svc in payload.services or []:
                service = services_by_id[svc.service_id]
                db.add(
                    OrderService(
                        order_id=order.id,
                        service_id=svc.service_id,
                        quantity=svc.quantity,
                        price_at_order=service.price,
                    )
                )

        await db.commit()
        await db.refresh(order)
        return order
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("order_create_failed", company_id=payload.company_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Не удалось создать заявку")


@router.get("", response_model=OrderList)
async def list_orders(
    company_id: int,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderList:
    """List orders by company with pagination."""
    if current_user.role in {"warehouse", "admin"}:
        company_result = await db.execute(select(Company).where(Company.id == company_id))
    else:
        company_result = await db.execute(
            select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
        )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    base_query = select(Order).where(Order.company_id == company_id).order_by(Order.created_at.desc())
    if status:
        statuses = [value.strip() for value in status.split(",") if value.strip()]
        if statuses:
            base_query = base_query.where(Order.status.in_(statuses))
    total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = int(total_result.scalar_one())
    offset = (page - 1) * limit
    conditions = [Order.company_id == company_id]
    if status:
        statuses = [value.strip() for value in status.split(",") if value.strip()]
        if statuses:
            conditions.append(Order.status.in_(statuses))
    result = await db.execute(
        select(Order, func.count(OrderPhoto.id))
        .outerjoin(OrderPhoto, OrderPhoto.order_id == Order.id)
        .where(*conditions)
        .group_by(Order.id)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items: list[OrderOut] = []
    for order, photo_count in result.all():
        items.append(
            OrderOut.model_validate(order, from_attributes=True).model_copy(
                update={"photo_count": int(photo_count)}
            )
        )
    return OrderList(items=items, total=total, page=page, limit=limit)


@router.get("/{order_id}/items", response_model=list[OrderItemOut])
async def list_order_items(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrderItemOut]:
    """List items for a specific order."""
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if current_user.role in {"warehouse", "admin"}:
        company_result = await db.execute(select(Company).where(Company.id == order.company_id))
    else:
        company_result = await db.execute(
            select(Company).where(Company.id == order.company_id, Company.user_id == current_user.id)
        )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")

    result = await db.execute(
        select(OrderItem, Product)
        .join(Product, Product.id == OrderItem.product_id)
        .where(OrderItem.order_id == order_id)
    )
    items: list[OrderItemOut] = []
    for item, product in result.all():
        items.append(
            OrderItemOut(
                id=item.id,
                product_id=item.product_id,
                product_name=product.name,
                barcode=product.barcode,
                brand=product.brand,
                size=product.size,
                color=product.color,
                wb_article=product.wb_article,
                wb_url=product.wb_url,
                packing_instructions=product.packing_instructions,
                supplier_name=product.supplier_name,
                planned_qty=item.planned_qty,
                received_qty=item.received_qty,
                defect_qty=item.defect_qty,
                packed_qty=item.packed_qty,
                adjustment_qty=item.adjustment_qty,
                adjustment_note=item.adjustment_note,
            )
        )
    return items


@router.patch("/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderOut:
    """Update order status."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if current_user.role in {"warehouse", "admin"}:
        company_result = await db.execute(
            select(Company).where(Company.id == order.company_id).options(joinedload(Company.user))
        )
    else:
        company_result = await db.execute(
            select(Company)
            .where(Company.id == order.company_id, Company.user_id == current_user.id)
            .options(joinedload(Company.user))
        )
    company = company_result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    telegram_id = company.user.telegram_id if company.user else None
    order_number = order.order_number
    new_status = payload.status
    order.status = new_status
    await db.commit()
    await db.refresh(order)
    if telegram_id and new_status in ("Принято", "Готово к отгрузке", "Завершено"):
        await send_notification(
            telegram_id,
            f"Заявка {order_number}: статус изменен на {new_status}.",
        )
    return order


@router.post("/{order_id}/photo")
async def upload_order_photo(
    order_id: int,
    file: UploadFile = File(...),
    photo_type: str | None = Query(None),
    product_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Upload order photo."""
    s3 = S3Service()
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Неподдерживаемый тип файла")
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Файл слишком большой")
    image = Image.open(BytesIO(data))
    image.thumbnail((1200, 1200))
    output = BytesIO()
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.save(output, format="JPEG")
    data = output.getvalue()
    photo_count = await db.execute(select(func.count()).select_from(OrderPhoto).where(OrderPhoto.order_id == order_id))
    if int(photo_count.scalar_one()) >= 20:
        raise HTTPException(status_code=400, detail="Достигнут лимит фотографий")

    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if current_user.role in {"warehouse", "admin"}:
        company_result = await db.execute(select(Company).where(Company.id == order.company_id))
    else:
        company_result = await db.execute(
            select(Company).where(Company.id == order.company_id, Company.user_id == current_user.id)
        )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    if product_id:
        product_result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id, OrderItem.product_id == product_id)
        )
        if not product_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Товар не входит в эту заявку")

    key = f"orders/{order_id}/{datetime.utcnow().timestamp()}_{file.filename}"
    s3.upload_bytes(key, data, file.content_type or "image/jpeg")
    url = s3.build_public_url(key)
    if not await s3.head_check(url):
        raise HTTPException(status_code=400, detail="Upload verification failed")

    photo = OrderPhoto(order_id=order_id, s3_key=key, photo_type=photo_type, product_id=product_id)
    db.add(photo)
    await db.commit()
    return {"key": key}


@router.get("/{order_id}/photos", response_model=list[OrderPhotoOut])
async def list_order_photos(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrderPhotoOut]:
    """List order photos."""
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if current_user.role in {"warehouse", "admin"}:
        company_result = await db.execute(select(Company).where(Company.id == order.company_id))
    else:
        company_result = await db.execute(
            select(Company).where(Company.id == order.company_id, Company.user_id == current_user.id)
        )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    result = await db.execute(select(OrderPhoto).where(OrderPhoto.order_id == order_id))
    photos = list(result.scalars().all())
    s3 = S3Service()
    response: list[OrderPhotoOut] = []
    for photo in photos:
        response.append(
            OrderPhotoOut(
                id=photo.id,
                s3_key=photo.s3_key,
                url=s3.build_public_url(photo.s3_key),
                photo_type=photo.photo_type,
                product_id=photo.product_id,
                created_at=photo.created_at,
            )
        )
    return response


@router.get("/{order_id}/export-receiving")
async def export_receiving_excel(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export receiving data for order to Excel."""
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if current_user.role in {"warehouse", "admin"}:
        company_result = await db.execute(select(Company).where(Company.id == order.company_id))
    else:
        company_result = await db.execute(
            select(Company).where(Company.id == order.company_id, Company.user_id == current_user.id)
        )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    result = await db.execute(
        select(OrderItem)
        .options(joinedload(OrderItem.product), joinedload(OrderItem.order))
        .where(OrderItem.order_id == order_id)
    )
    items = list(result.unique().scalars().all())
    if not items:
        raise HTTPException(status_code=400, detail="Нет позиций для выгрузки")
    buffer = export_receiving(items)
    filename = f"Приемка_заявка_{order.order_number}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": content_disposition(filename)},
    )
