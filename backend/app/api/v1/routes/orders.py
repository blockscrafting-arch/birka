"""Order endpoints."""
from datetime import date, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.models.company import Company
from app.db.models.order import Order, OrderItem
from app.db.models.order_counter import OrderCounter
from app.db.models.order_photo import OrderPhoto
from app.db.models.product import Product
from app.db.session import get_db
from app.schemas.order import OrderCreate, OrderItemOut, OrderOut, OrderPhotoOut, OrderStatusUpdate
from app.services.s3 import S3Service
from app.core.config import settings
from app.core.utils import is_allowed_image_bytes, sanitize_upload_filename
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

    today = date.today()
    prefix = datetime.utcnow().strftime("Заявка %d/%m/%y")
    async with db.begin():
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
    total_planned = sum(item.planned_qty for item in payload.items)
    order = Order(
        company_id=payload.company_id,
        order_number=order_number,
        status="На приемке",
        destination=payload.destination,
        planned_qty=total_planned,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    for item in payload.items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                planned_qty=item.planned_qty,
            )
        )
    await db.commit()
    return order


@router.get("", response_model=list[OrderOut])
async def list_orders(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrderOut]:
    """List orders by company."""
    company_result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    result = await db.execute(select(Order).where(Order.company_id == company_id))
    return list(result.scalars().all())


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
                planned_qty=item.planned_qty,
                received_qty=item.received_qty,
                defect_qty=item.defect_qty,
                packed_qty=item.packed_qty,
            )
        )
    return items


@router.get("/{order_id}/photos", response_model=list[OrderPhotoOut])
async def list_order_photos(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrderPhotoOut]:
    """List photos for a specific order."""
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    company_result = await db.execute(
        select(Company).where(Company.id == order.company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")

    photos_result = await db.execute(select(OrderPhoto).where(OrderPhoto.order_id == order_id))
    photos = photos_result.scalars().all()
    s3 = S3Service()
    return [
        OrderPhotoOut(
            id=photo.id,
            url=s3.build_public_url(photo.s3_key),
            photo_type=photo.photo_type,
            created_at=photo.created_at.isoformat(),
        )
        for photo in photos
    ]


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
    company_result = await db.execute(
        select(Company).where(Company.id == order.company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    order.status = payload.status
    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{order_id}/photo")
async def upload_order_photo(
    order_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Upload order photo. Permissions and photo limit checked before reading file."""
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    company_result = await db.execute(
        select(Company).where(Company.id == order.company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    photo_count = await db.execute(select(func.count()).select_from(OrderPhoto).where(OrderPhoto.order_id == order_id))
    if int(photo_count.scalar_one()) >= 20:
        raise HTTPException(status_code=400, detail="Достигнут лимит фото (20)")

    s3 = S3Service()
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Неподдерживаемый тип файла")
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Файл слишком большой")
    if not is_allowed_image_bytes(data):
        raise HTTPException(status_code=400, detail="Неподдерживаемый тип файла")
    try:
        image = Image.open(BytesIO(data))
        image.thumbnail((1200, 1200))
        output = BytesIO()
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(output, format="JPEG")
        data = output.getvalue()
    except (UnidentifiedImageError, OSError) as e:
        logger.warning("order_photo_image_error", order_id=order_id, error=str(e))
        raise HTTPException(status_code=400, detail="Не удалось обработать изображение")
    key = f"orders/{order_id}/{datetime.utcnow().timestamp()}_{sanitize_upload_filename(file.filename)}"
    s3.upload_bytes(key, data, file.content_type or "image/jpeg")
    url = s3.build_public_url(key)
    if not await s3.head_check(url):
        raise HTTPException(status_code=400, detail="Не удалось проверить загрузку")

    photo = OrderPhoto(order_id=order_id, s3_key=key, photo_type="order")
    db.add(photo)
    await db.commit()
    return {"key": key}
