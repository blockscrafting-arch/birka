"""Shipment request endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.core.crypto import decrypt_value
from app.core.logging import logger
from app.db.models.company import Company
from app.db.models.company_api_keys import CompanyAPIKeys
from app.db.models.fbo_supply import FBOSupply
from app.db.models.order import Order
from app.db.models.shipment_request import ShipmentRequest
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.order import OrderOut
from app.schemas.shipping import ShipmentRequestCreate, ShipmentRequestList, ShipmentRequestOut
from app.schemas.shipping import ShipmentRequestStatusUpdate
from app.services.ozon_api import OzonAPI
from app.services.s3 import S3Service
from app.services.wb_api import WildberriesAPI

router = APIRouter()

ALLOWED_BARCODE_CONTENT_TYPES = (
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
)
ALLOWED_BOX_BARCODES_EXTRA = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
)


def _shipment_request_to_out(request: ShipmentRequest, s3: S3Service) -> ShipmentRequestOut:
    """Build ShipmentRequestOut from ORM with order_number and barcode URLs."""
    order_number = request.order.order_number if request.order else None
    supply_barcode_url = s3.build_public_url(request.supply_barcode_key) if request.supply_barcode_key else None
    box_barcodes_url = s3.build_public_url(request.box_barcodes_key) if request.box_barcodes_key else None
    return ShipmentRequestOut(
        id=request.id,
        company_id=request.company_id,
        order_id=request.order_id,
        order_number=order_number,
        fbo_supply_id=getattr(request, "fbo_supply_id", None),
        destination_type=request.destination_type,
        destination_comment=request.destination_comment,
        warehouse_name=request.warehouse_name,
        delivery_date=request.delivery_date,
        supply_barcode_url=supply_barcode_url,
        box_barcodes_url=box_barcodes_url,
        status=request.status,
        created_at=request.created_at,
    )


async def _validate_marketplace_keys(
    db: AsyncSession, company_id: int, destination_type: str
) -> None:
    """If destination is WB or Ozon, ensure company has API keys and they work. Raises HTTPException on failure."""
    dest = (destination_type or "").strip().upper()
    if dest not in ("WB", "OZON"):
        return
    result = await db.execute(
        select(CompanyAPIKeys).where(CompanyAPIKeys.company_id == company_id)
    )
    keys = result.scalar_one_or_none()
    secret = settings.ENCRYPTION_KEY or ""
    if dest == "WB":
        if not keys or not keys.wb_api_key:
            raise HTTPException(
                status_code=400,
                detail="Укажите API-ключ Wildberries в настройках компании (API-ключи WB / Ozon).",
            )
        wb_key = decrypt_value(keys.wb_api_key, secret) or keys.wb_api_key
        api = WildberriesAPI(api_key=wb_key)
        supplies = await api.get_supplies(limit=1)
        if supplies is None:
            raise HTTPException(
                status_code=400,
                detail="Не удалось подключиться к API Wildberries. Проверьте ключ в настройках компании.",
            )
    else:  # OZON
        if not keys or not keys.ozon_client_id or not keys.ozon_api_key:
            raise HTTPException(
                status_code=400,
                detail="Укажите Client ID и API Key Ozon в настройках компании (API-ключи WB / Ozon).",
            )
        ozon_cid = decrypt_value(keys.ozon_client_id, secret) or keys.ozon_client_id
        ozon_key = decrypt_value(keys.ozon_api_key, secret) or keys.ozon_api_key
        api = OzonAPI(client_id=ozon_cid, api_key=ozon_key)
        orders = await api.list_supply_orders()
        if orders is None:
            raise HTTPException(
                status_code=400,
                detail="Не удалось подключиться к API Ozon. Проверьте Client ID и API Key в настройках компании.",
            )
    return None


@router.get("/orders-ready", response_model=list[OrderOut])
async def get_orders_ready_for_shipping(
    company_id: int = Query(..., description="Company ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrderOut]:
    """Return orders with status 'Готово к отгрузке' for the company (for shipment creation dropdown)."""
    if current_user.role in {"warehouse", "admin"}:
        company_result = await db.execute(select(Company).where(Company.id == company_id))
    else:
        company_result = await db.execute(
            select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
        )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    result = await db.execute(
        select(Order).where(
            Order.company_id == company_id,
            Order.status == "Готово к отгрузке",
        ).order_by(Order.created_at.desc())
    )
    orders = list(result.scalars().all())
    return [OrderOut.model_validate(o, from_attributes=True) for o in orders]


@router.post("", response_model=ShipmentRequestOut)
async def create_shipment_request(
    payload: ShipmentRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShipmentRequestOut:
    """Create shipment request. For WB/Ozon validates company API keys and marketplace connection."""
    company_result = await db.execute(
        select(Company).where(Company.id == payload.company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")

    order_result = await db.execute(
        select(Order).where(
            Order.id == payload.order_id,
            Order.company_id == payload.company_id,
            Order.status == "Готово к отгрузке",
        )
    )
    if not order_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Заявка не найдена или не имеет статус «Готово к отгрузке».",
        )

    existing = await db.execute(
        select(ShipmentRequest.id).where(
            ShipmentRequest.company_id == payload.company_id,
            ShipmentRequest.order_id == payload.order_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="На эту заявку уже создана отгрузка. Выберите другую заявку.",
        )

    await _validate_marketplace_keys(db, payload.company_id, payload.destination_type)

    try:
        request = ShipmentRequest(
            company_id=payload.company_id,
            order_id=payload.order_id,
            destination_type=payload.destination_type,
            destination_comment=payload.destination_comment,
            warehouse_name=payload.warehouse_name,
            delivery_date=payload.delivery_date,
        )
        db.add(request)
        await db.flush()
        dest = (payload.destination_type or "").strip().upper()
        if dest in ("WB", "OZON"):
            keys_r = await db.execute(
                select(CompanyAPIKeys).where(CompanyAPIKeys.company_id == payload.company_id)
            )
            keys = keys_r.scalar_one_or_none()
            secret = settings.ENCRYPTION_KEY or ""
            external_id: str | None = None
            marketplace = dest.lower()
            box_count = getattr(payload, "box_count", None) or 0
            if dest == "WB" and keys and box_count > 0:
                wb_key = decrypt_value(keys.wb_api_key, secret)
                if wb_key:
                    api = WildberriesAPI(api_key=wb_key)
                    external_id = await api.create_supply(name="Поставка")
                    if external_id:
                        await api.create_supply_boxes(external_id, box_count)
            elif dest == "OZON" and keys:
                ozon_cid = decrypt_value(keys.ozon_client_id, secret)
                ozon_key = decrypt_value(keys.ozon_api_key, secret)
                if ozon_cid and ozon_key:
                    api = OzonAPI(client_id=ozon_cid, api_key=ozon_key)
                    sid = await api.create_supply_draft()
                    external_id = str(sid) if sid is not None else None
            fbo = FBOSupply(
                company_id=payload.company_id,
                order_id=payload.order_id,
                marketplace=marketplace,
                external_supply_id=external_id,
                status="created" if external_id else "draft",
            )
            db.add(fbo)
            await db.flush()
            request.fbo_supply_id = fbo.id
        await db.commit()
        await db.refresh(request)
        result2 = await db.execute(
            select(ShipmentRequest).options(joinedload(ShipmentRequest.order)).where(ShipmentRequest.id == request.id)
        )
        request = result2.unique().scalar_one()
        s3 = S3Service()
        return _shipment_request_to_out(request, s3)
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("shipment_request_failed", company_id=payload.company_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Не удалось создать заявку на отгрузку")


@router.get("", response_model=ShipmentRequestList)
async def list_shipment_requests(
    company_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShipmentRequestList:
    """List shipment requests by company."""
    if current_user.role in {"warehouse", "admin"}:
        company_result = await db.execute(select(Company).where(Company.id == company_id))
    else:
        company_result = await db.execute(
            select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
        )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    base_query = select(ShipmentRequest).where(ShipmentRequest.company_id == company_id)
    total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = int(total_result.scalar_one())
    offset = (page - 1) * limit
    result = await db.execute(
        base_query.options(joinedload(ShipmentRequest.order)).offset(offset).limit(limit)
    )
    requests = list(result.unique().scalars().all())
    s3 = S3Service()
    items = [_shipment_request_to_out(r, s3) for r in requests]
    return ShipmentRequestList(items=items, total=total, page=page, limit=limit)


@router.patch("/{request_id}/status", response_model=ShipmentRequestOut)
async def update_shipment_status(
    request_id: int,
    payload: ShipmentRequestStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShipmentRequestOut:
    """Update shipment request status."""
    result = await db.execute(
        select(ShipmentRequest).options(joinedload(ShipmentRequest.order)).where(ShipmentRequest.id == request_id)
    )
    request = result.unique().scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Заявка на отгрузку не найдена")
    if current_user.role not in {"warehouse", "admin"}:
        company_result = await db.execute(
            select(Company).where(Company.id == request.company_id, Company.user_id == current_user.id)
        )
        if not company_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Компания не найдена")
    try:
        request.status = payload.status
        await db.commit()
        await db.refresh(request)
        result2 = await db.execute(
            select(ShipmentRequest).options(joinedload(ShipmentRequest.order)).where(ShipmentRequest.id == request_id)
        )
        request = result2.unique().scalar_one()
        s3 = S3Service()
        return _shipment_request_to_out(request, s3)
    except Exception as exc:
        await db.rollback()
        logger.exception("shipment_status_failed", request_id=request_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Не удалось обновить статус отгрузки")


@router.post("/{request_id}/supply-barcode")
async def upload_supply_barcode(
    request_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Upload supply barcode file (PDF or image) for shipment request."""
    result = await db.execute(
        select(ShipmentRequest).where(ShipmentRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Заявка на отгрузку не найдена")
    if current_user.role not in {"warehouse", "admin"}:
        company_result = await db.execute(
            select(Company).where(Company.id == req.company_id, Company.user_id == current_user.id)
        )
        if not company_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Компания не найдена")
    content_type = (file.content_type or "").strip().lower()
    if content_type not in ALLOWED_BARCODE_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Разрешены только PDF или изображения (JPEG, PNG, GIF, WebP)",
        )
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Файл слишком большой")
    s3 = S3Service()
    key = f"shipping/{request_id}/supply_barcode_{datetime.utcnow().timestamp():.0f}_{file.filename or 'file'}"
    s3.upload_bytes(key, data, content_type)
    url = s3.build_public_url(key)
    if not await s3.head_check(url):
        raise HTTPException(status_code=400, detail="Проверка загрузки не прошла")
    req.supply_barcode_key = key
    await db.commit()
    return {"key": key}


@router.post("/{request_id}/box-barcodes")
async def upload_box_barcodes(
    request_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Upload box barcodes file (PDF or image) for shipment request."""
    result = await db.execute(
        select(ShipmentRequest).where(ShipmentRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Заявка на отгрузку не найдена")
    if current_user.role not in {"warehouse", "admin"}:
        company_result = await db.execute(
            select(Company).where(Company.id == req.company_id, Company.user_id == current_user.id)
        )
        if not company_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Компания не найдена")
    content_type = (file.content_type or "").strip().lower()
    if content_type not in (*ALLOWED_BARCODE_CONTENT_TYPES, *ALLOWED_BOX_BARCODES_EXTRA):
        raise HTTPException(
            status_code=400,
            detail="Разрешены PDF, изображения (JPEG, PNG, GIF, WebP) или Excel",
        )
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Файл слишком большой")
    s3 = S3Service()
    key = f"shipping/{request_id}/box_barcodes_{datetime.utcnow().timestamp():.0f}_{file.filename or 'file'}"
    s3.upload_bytes(key, data, content_type)
    url = s3.build_public_url(key)
    if not await s3.head_check(url):
        raise HTTPException(status_code=400, detail="Проверка загрузки не прошла")
    req.box_barcodes_key = key
    await db.commit()
    return {"key": key}
