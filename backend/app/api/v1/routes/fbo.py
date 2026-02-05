"""FBO supply endpoints (WB/Ozon)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.core.crypto import decrypt_value
from app.db.models.company import Company
from app.db.models.company_api_keys import CompanyAPIKeys
from app.db.models.fbo_supply import FBOSupply, FBOSupplyBox
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.fbo import (
    BoxStickersOut,
    BoxStickerOut,
    FBOSupplyCreate,
    FBOSupplyImportBarcodes,
    FBOSupplyList,
    FBOSupplyOut,
    FBOSupplyBoxOut,
)
from app.services.ozon_api import OzonAPI
from app.services.wb_api import WildberriesAPI

router = APIRouter()


def _company_access(company: Company, user: User) -> bool:
    return company.user_id == user.id or user.role == "admin"


async def _get_company_or_404(db: AsyncSession, company_id: int, user: User) -> Company:
    if user.role in {"warehouse", "admin"}:
        r = await db.execute(select(Company).where(Company.id == company_id))
    else:
        r = await db.execute(
            select(Company).where(Company.id == company_id, Company.user_id == user.id)
        )
    company = r.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")
    return company


def _supply_to_out(supply: FBOSupply) -> FBOSupplyOut:
    boxes = [FBOSupplyBoxOut.model_validate(b, from_attributes=True) for b in supply.boxes]
    return FBOSupplyOut(
        id=supply.id,
        order_id=supply.order_id,
        company_id=supply.company_id,
        marketplace=supply.marketplace,
        external_supply_id=supply.external_supply_id,
        status=supply.status,
        warehouse_name=supply.warehouse_name,
        created_at=supply.created_at,
        boxes=sorted(boxes, key=lambda x: x.box_number),
    )


@router.get("/supplies", response_model=FBOSupplyList)
async def list_fbo_supplies(
    company_id: int = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FBOSupplyList:
    """List FBO supplies for company."""
    await _get_company_or_404(db, company_id, current_user)

    count_q = await db.execute(
        select(func.count()).select_from(FBOSupply).where(FBOSupply.company_id == company_id)
    )
    total = count_q.scalar() or 0
    offset = (page - 1) * limit
    result = await db.execute(
        select(FBOSupply)
        .where(FBOSupply.company_id == company_id)
        .options(joinedload(FBOSupply.boxes))
        .order_by(FBOSupply.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    supplies = list(result.unique().scalars().all())
    items = [_supply_to_out(s) for s in supplies]
    return FBOSupplyList(items=items, total=total, page=page, limit=limit)


@router.get("/supplies/{supply_id}", response_model=FBOSupplyOut)
async def get_fbo_supply(
    supply_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FBOSupplyOut:
    """Get FBO supply by id."""
    result = await db.execute(
        select(FBOSupply)
        .where(FBOSupply.id == supply_id)
        .options(joinedload(FBOSupply.boxes))
    )
    supply = result.unique().scalar_one_or_none()
    if not supply:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Поставка не найдена")
    await _get_company_or_404(db, supply.company_id, current_user)
    return _supply_to_out(supply)


@router.post("/supplies", response_model=FBOSupplyOut)
async def create_fbo_supply(
    payload: FBOSupplyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FBOSupplyOut:
    """Create FBO supply draft. Optionally create supply in WB/Ozon and store external_supply_id."""
    await _get_company_or_404(db, payload.company_id, current_user)
    marketplace = (payload.marketplace or "").strip().lower()
    if marketplace not in ("wb", "ozon"):
        raise HTTPException(status_code=400, detail="marketplace должен быть wb или ozon")

    external_id: str | None = None
    if marketplace == "wb":
        box_count = getattr(payload, "box_count", None) or 0
        if box_count > 0:
            keys_r = await db.execute(
                select(CompanyAPIKeys).where(CompanyAPIKeys.company_id == payload.company_id)
            )
            keys = keys_r.scalar_one_or_none()
            secret = settings.ENCRYPTION_KEY or ""
            wb_key = decrypt_value(keys.wb_api_key, secret) if keys else None
            if wb_key:
                api = WildberriesAPI(api_key=wb_key)
                external_id = await api.create_supply(name="Поставка")
                if external_id:
                    await api.create_supply_boxes(external_id, box_count)
    elif marketplace == "ozon":
        keys_r = await db.execute(
            select(CompanyAPIKeys).where(CompanyAPIKeys.company_id == payload.company_id)
        )
        keys = keys_r.scalar_one_or_none()
        secret = settings.ENCRYPTION_KEY or ""
        ozon_cid = decrypt_value(keys.ozon_client_id, secret) if keys else None
        ozon_key = decrypt_value(keys.ozon_api_key, secret) if keys else None
        if ozon_cid and ozon_key:
            api = OzonAPI(client_id=ozon_cid, api_key=ozon_key)
            sid = await api.create_supply_draft()
            external_id = str(sid) if sid is not None else None

    supply = FBOSupply(
        company_id=payload.company_id,
        order_id=payload.order_id,
        marketplace=marketplace,
        external_supply_id=external_id,
        status="created" if external_id else "draft",
    )
    db.add(supply)
    await db.commit()
    await db.refresh(supply)
    result2 = await db.execute(
        select(FBOSupply).where(FBOSupply.id == supply.id).options(joinedload(FBOSupply.boxes))
    )
    supply = result2.unique().scalar_one()
    return _supply_to_out(supply)


@router.post("/supplies/{supply_id}/sync", response_model=FBOSupplyOut)
async def sync_fbo_supply_barcodes(
    supply_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FBOSupplyOut:
    """Fetch box barcodes from WB/Ozon and update supply boxes."""
    result = await db.execute(
        select(FBOSupply).where(FBOSupply.id == supply_id).options(joinedload(FBOSupply.boxes))
    )
    supply = result.unique().scalar_one_or_none()
    if not supply:
        raise HTTPException(status_code=404, detail="Поставка не найдена")
    await _get_company_or_404(db, supply.company_id, current_user)
    if not supply.external_supply_id:
        raise HTTPException(status_code=400, detail="Нет внешнего ID поставки для синхронизации")

    keys_r = await db.execute(
        select(CompanyAPIKeys).where(CompanyAPIKeys.company_id == supply.company_id)
    )
    keys = keys_r.scalar_one_or_none()
    secret = settings.ENCRYPTION_KEY or ""
    boxes_data: list[tuple[str | None, str]] = []  # (external_box_id, external_barcode)
    if supply.marketplace == "wb":
        wb_key = decrypt_value(keys.wb_api_key, secret) if keys else None
        if not wb_key:
            raise HTTPException(status_code=400, detail="Укажите API-ключ WB для компании")
        api = WildberriesAPI(api_key=wb_key)
        wb_boxes = await api.get_supply_boxes(supply.external_supply_id)
        for b in wb_boxes:
            bid = b.get("id")
            if bid:
                boxes_data.append((str(bid), str(bid)))
    elif supply.marketplace == "ozon":
        ozon_cid = decrypt_value(keys.ozon_client_id, secret) if keys else None
        ozon_key = decrypt_value(keys.ozon_api_key, secret) if keys else None
        if not ozon_cid or not ozon_key:
            raise HTTPException(status_code=400, detail="Укажите Client ID и API Key Ozon для компании")
        api = OzonAPI(client_id=ozon_cid, api_key=ozon_key)
        try:
            sid = int(supply.external_supply_id)
        except ValueError:
            sid = 0
        if sid:
            barcodes = await api.get_supply_barcodes(sid)
            for b in barcodes:
                if b:
                    boxes_data.append((None, b.strip()))

    for box in supply.boxes:
        await db.delete(box)
    await db.flush()
    for i, (ext_box_id, ext_barcode) in enumerate(boxes_data):
        box = FBOSupplyBox(
            supply_id=supply.id,
            box_number=i + 1,
            external_box_id=ext_box_id,
            external_barcode=ext_barcode,
        )
        db.add(box)
    await db.commit()
    result2 = await db.execute(
        select(FBOSupply).where(FBOSupply.id == supply_id).options(joinedload(FBOSupply.boxes))
    )
    supply = result2.unique().scalar_one()
    return _supply_to_out(supply)


@router.post("/supplies/{supply_id}/box-stickers", response_model=BoxStickersOut)
async def get_fbo_box_stickers(
    supply_id: int,
    fmt: str = Query("png", description="Формат стикера: png, svg, zplv, zplh"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BoxStickersOut:
    """Get box stickers for WB supply (for print). Returns base64 images."""
    if fmt not in ("png", "svg", "zplv", "zplh"):
        raise HTTPException(status_code=400, detail="Формат стикера: png, svg, zplv или zplh")
    result = await db.execute(
        select(FBOSupply).where(FBOSupply.id == supply_id).options(joinedload(FBOSupply.boxes))
    )
    supply = result.unique().scalar_one_or_none()
    if not supply:
        raise HTTPException(status_code=404, detail="Поставка не найдена")
    await _get_company_or_404(db, supply.company_id, current_user)
    if supply.marketplace != "wb" or not supply.external_supply_id:
        raise HTTPException(
            status_code=400,
            detail="Стикеры коробов доступны только для поставок WB с созданной поставкой в кабинете",
        )
    trbx_ids = [b.external_box_id for b in supply.boxes if b.external_box_id]
    if not trbx_ids:
        return BoxStickersOut(stickers=[])
    keys_r = await db.execute(
        select(CompanyAPIKeys).where(CompanyAPIKeys.company_id == supply.company_id)
    )
    keys = keys_r.scalar_one_or_none()
    if not keys or not keys.wb_api_key:
        raise HTTPException(status_code=400, detail="Укажите API-ключ WB для компании")
    secret = settings.ENCRYPTION_KEY or ""
    wb_key = decrypt_value(keys.wb_api_key, secret)
    if not wb_key:
        raise HTTPException(status_code=400, detail="Укажите API-ключ WB для компании")
    api = WildberriesAPI(api_key=wb_key)
    raw = await api.get_box_stickers(supply.external_supply_id, trbx_ids, fmt=fmt)
    content_type = "image/png" if fmt == "png" else "image/svg+xml" if fmt == "svg" else "application/octet-stream"
    stickers = []
    for s in raw or []:
        trbx_id = s.get("trbxId") or s.get("trbx_id") or ""
        barcode = s.get("barcode")
        file_b64 = s.get("file") or ""
        stickers.append(
            BoxStickerOut(
                trbx_id=trbx_id,
                barcode=barcode,
                file_base64=file_b64,
                content_type=content_type,
            )
        )
    return BoxStickersOut(stickers=stickers)


@router.post("/supplies/{supply_id}/import-barcodes", response_model=FBOSupplyOut)
async def import_fbo_barcodes(
    supply_id: int,
    payload: FBOSupplyImportBarcodes,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FBOSupplyOut:
    """Import box barcodes manually (barcodes in order = box 1, 2, ...). Append mode: new boxes are added to existing ones; to replace, use sync first or delete supply boxes elsewhere."""
    result = await db.execute(
        select(FBOSupply).where(FBOSupply.id == supply_id).options(joinedload(FBOSupply.boxes))
    )
    supply = result.unique().scalar_one_or_none()
    if not supply:
        raise HTTPException(status_code=404, detail="Поставка не найдена")
    await _get_company_or_404(db, supply.company_id, current_user)

    for i, barcode in enumerate(payload.barcodes or []):
        b = (barcode or "").strip()
        if not b:
            continue
        box = FBOSupplyBox(
            supply_id=supply.id,
            box_number=i + 1,
            external_box_id=None,
            external_barcode=b,
        )
        db.add(box)
    await db.commit()
    result2 = await db.execute(
        select(FBOSupply).where(FBOSupply.id == supply_id).options(joinedload(FBOSupply.boxes))
    )
    supply = result2.unique().scalar_one()
    return _supply_to_out(supply)
