"""Order endpoints."""
from datetime import date, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.models.company import Company
from app.db.models.order import Order, OrderItem
from app.db.models.order_counter import OrderCounter
from app.db.models.order_photo import OrderPhoto
from app.db.session import get_db
from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate
from app.services.s3 import S3Service
from app.core.config import settings
from app.db.models.user import User

router = APIRouter()


@router.post("/", response_model=OrderOut)
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
        raise HTTPException(status_code=404, detail="Company not found")

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


@router.get("/", response_model=list[OrderOut])
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
        raise HTTPException(status_code=404, detail="Company not found")
    result = await db.execute(select(Order).where(Order.company_id == company_id))
    return list(result.scalars().all())


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
        raise HTTPException(status_code=404, detail="Order not found")
    company_result = await db.execute(
        select(Company).where(Company.id == order.company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")
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
    """Upload order photo."""
    s3 = S3Service()
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large")
    image = Image.open(BytesIO(data))
    image.thumbnail((1200, 1200))
    output = BytesIO()
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.save(output, format="JPEG")
    data = output.getvalue()
    photo_count = await db.execute(select(func.count()).select_from(OrderPhoto).where(OrderPhoto.order_id == order_id))
    if int(photo_count.scalar_one()) >= 20:
        raise HTTPException(status_code=400, detail="Photo limit reached")

    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    company_result = await db.execute(
        select(Company).where(Company.id == order.company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")

    key = f"orders/{order_id}/{datetime.utcnow().timestamp()}_{file.filename}"
    s3.upload_bytes(key, data, file.content_type or "image/jpeg")
    url = s3.build_public_url(key)
    if not await s3.head_check(url):
        raise HTTPException(status_code=400, detail="Upload verification failed")

    photo = OrderPhoto(order_id=order_id, s3_key=key, photo_type="order")
    db.add(photo)
    await db.commit()
    return {"key": key}
