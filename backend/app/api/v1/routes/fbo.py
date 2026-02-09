"""FBO supplies endpoints (WB/Ozon)."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_user
from app.db.models.company import Company
from app.db.models.fbo_supply import FBOSupply, FBOSupplyBox, FBOSupplyItem
from app.db.models.product import Product
from app.db.session import get_db
from app.schemas.fbo import (
    FBOBarcodeImport,
    FBOSupplyBoxOut,
    FBOSupplyCreate,
    FBOSupplyItemOut,
    FBOSupplyOut,
    FBOSupplyStatusUpdate,
)
from app.services.marketplace import get_ozon_client, get_wb_client
from app.db.models.user import User

router = APIRouter()


def _supply_query():
    """Query supplies with boxes and items loaded."""
    return select(FBOSupply).options(
        selectinload(FBOSupply.boxes).selectinload(FBOSupplyBox.items),
        selectinload(FBOSupply.company),
    )


async def _ensure_supply_access(supply_id: int, current_user: User, db: AsyncSession) -> FBOSupply:
    """Load supply; allow if user owns company or is warehouse/admin."""
    result = await db.execute(_supply_query().where(FBOSupply.id == supply_id))
    supply = result.scalar_one_or_none()
    if not supply:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Поставка не найдена")
    if current_user.role not in ("warehouse", "admin") and supply.company.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён")
    return supply


def _supply_to_out(supply: FBOSupply) -> FBOSupplyOut:
    """Build FBOSupplyOut from ORM with boxes/items."""
    boxes_out = [
        FBOSupplyBoxOut(
            id=b.id,
            supply_id=b.supply_id,
            box_number=b.box_number,
            barcode=b.barcode,
            sticker_s3_key=b.sticker_s3_key,
            external_box_id=b.external_box_id,
            items=[FBOSupplyItemOut.model_validate(i) for i in b.items],
        )
        for b in supply.boxes
    ]
    return FBOSupplyOut(
        id=supply.id,
        company_id=supply.company_id,
        marketplace=supply.marketplace,
        external_supply_id=supply.external_supply_id,
        warehouse_name=supply.warehouse_name,
        status=supply.status,
        created_at=supply.created_at,
        updated_at=supply.updated_at,
        boxes=boxes_out,
    )


@router.post("/supplies", response_model=FBOSupplyOut)
async def create_fbo_supply(
    payload: FBOSupplyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FBOSupplyOut:
    """Create FBO supply (draft)."""
    company_result = await db.execute(
        select(Company).where(Company.id == payload.company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")
    supply = FBOSupply(
        company_id=payload.company_id,
        marketplace=payload.marketplace,
        warehouse_name=payload.warehouse_name or None,
        status="draft",
    )
    db.add(supply)
    await db.flush()
    for box_in in payload.boxes:
        box = FBOSupplyBox(supply_id=supply.id, box_number=box_in.box_number)
        db.add(box)
        await db.flush()
        for item_in in box_in.items:
            db.add(
                FBOSupplyItem(
                    box_id=box.id,
                    product_id=item_in.product_id,
                    quantity=item_in.quantity,
                    barcode=item_in.barcode,
                )
            )
    await db.commit()
    result = await db.execute(_supply_query().where(FBOSupply.id == supply.id))
    supply = result.scalar_one()
    return _supply_to_out(supply)


@router.get("/supplies", response_model=list[FBOSupplyOut])
async def list_fbo_supplies(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FBOSupplyOut]:
    """List FBO supplies for a company."""
    company_result = await db.execute(select(Company).where(Company.id == company_id))
    company = company_result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")
    if current_user.role not in ("warehouse", "admin") and company.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён")
    result = await db.execute(_supply_query().where(FBOSupply.company_id == company_id))
    supplies = list(result.scalars().all())
    return [_supply_to_out(s) for s in supplies]


@router.get("/supplies/{supply_id}", response_model=FBOSupplyOut)
async def get_fbo_supply(
    supply_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FBOSupplyOut:
    """Get FBO supply by id."""
    supply = await _ensure_supply_access(supply_id, current_user, db)
    return _supply_to_out(supply)


@router.patch("/supplies/{supply_id}", response_model=FBOSupplyOut)
async def update_fbo_supply_status(
    supply_id: int,
    payload: FBOSupplyStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FBOSupplyOut:
    """Update supply status."""
    supply = await _ensure_supply_access(supply_id, current_user, db)
    supply.status = payload.status
    await db.commit()
    result = await db.execute(_supply_query().where(FBOSupply.id == supply_id))
    supply = result.scalar_one()
    return _supply_to_out(supply)


@router.delete("/supplies/{supply_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fbo_supply(
    supply_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete supply (only draft)."""
    supply = await _ensure_supply_access(supply_id, current_user, db)
    if supply.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Можно удалить только поставку в статусе draft",
        )
    await db.delete(supply)
    await db.commit()


async def _ozon_sync_supply(supply: FBOSupply, ozon, db: AsyncSession) -> None:
    """Create Ozon FBO supply: draft -> supply -> cargoes, save external_supply_id and external_box_id."""
    product_ids = set()
    for box in supply.boxes:
        for item in box.items:
            product_ids.add(item.product_id)
    if not product_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет позиций для отправки")
    result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
    products = {p.id: p for p in result.scalars().all()}
    offer_quant: dict[str, int] = {}
    for box in supply.boxes:
        for item in box.items:
            p = products.get(item.product_id)
            if not p or not (p.ozon_article or "").strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"У товара (product_id={item.product_id}) не задан артикул Ozon (offer_id)",
                )
            oid = (p.ozon_article or "").strip()
            offer_quant[oid] = offer_quant.get(oid, 0) + item.quantity
    offer_ids = list(offer_quant.keys())
    offer_to_sku = await ozon.get_products_by_offer_id(offer_ids)
    missing = [o for o in offer_ids if o not in offer_to_sku]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ozon не вернул sku для артикулов: {missing[:5]}{'...' if len(missing) > 5 else ''}",
        )
    draft_items = [{"sku": offer_to_sku[o], "quantity": q} for o, q in offer_quant.items()]
    op_id = await ozon.create_supply_draft(draft_items)
    if not op_id:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Не удалось создать черновик в Ozon")
    draft_info = await ozon.get_draft_create_info(op_id)
    if not draft_info:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Черновик Ozon не создан или истёк")
    draft_id = draft_info.get("draft_id")
    warehouse_id = draft_info.get("warehouse_id")
    timeslots = draft_info.get("timeslots") or []
    if draft_id is None or warehouse_id is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Нет draft_id или warehouse_id в ответе Ozon")
    timeslot = None
    if timeslots and isinstance(timeslots, list) and len(timeslots) > 0:
        ts = timeslots[0] if isinstance(timeslots[0], dict) else None
        if ts:
            timeslot = {
                "from_in_timezone": ts.get("from_in_timezone", ""),
                "to_in_timezone": ts.get("to_in_timezone", ""),
            }
    if not timeslot:
        timeslot = {"from_in_timezone": "2025-12-31T09:00:00Z", "to_in_timezone": "2025-12-31T18:00:00Z"}
    supply_op_id = await ozon.create_supply_from_draft(int(draft_id), int(warehouse_id), timeslot)
    if not supply_op_id:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Не удалось создать поставку из черновика Ozon")
    supply_ids = await ozon.get_supply_create_status(supply_op_id)
    if not supply_ids:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Поставка Ozon не создана (таймаут или ошибка)")
    external_supply_id = supply_ids[0]
    cargoes_payload = []
    for box in supply.boxes:
        box_items = []
        for item in box.items:
            p = products.get(item.product_id)
            if p and (p.ozon_article or "").strip():
                box_items.append({"offer_id": (p.ozon_article or "").strip(), "quantity": item.quantity})
        cargoes_payload.append(box_items)
    cargo_op_id = await ozon.create_cargoes(int(external_supply_id), cargoes_payload)
    if not cargo_op_id:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Не удалось создать грузоместа в Ozon")
    cargo_ids = await ozon.get_cargoes_create_info(cargo_op_id)
    supply.external_supply_id = str(external_supply_id)
    supply.status = "active"
    if cargo_ids and len(cargo_ids) >= len(supply.boxes):
        for i, box in enumerate(supply.boxes):
            if i < len(cargo_ids):
                box.external_box_id = cargo_ids[i]
    await db.commit()


@router.post("/supplies/{supply_id}/sync", response_model=FBOSupplyOut)
async def sync_fbo_supply(
    supply_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FBOSupplyOut:
    """Sync supply to marketplace (create in WB/Ozon, save external_supply_id and external_box_id)."""
    supply = await _ensure_supply_access(supply_id, current_user, db)
    if supply.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Синхронизировать можно только draft")
    if supply.marketplace == "wb":
        wb = await get_wb_client(supply.company_id, db)
        name = f"Birka supply #{supply.id}"
        created = await wb.create_supply(name)
        if created and created.get("id"):
            supply.external_supply_id = str(created["id"])
            supply.status = "active"
            await db.commit()
    elif supply.marketplace == "ozon":
        ozon = await get_ozon_client(supply.company_id, db)
        await _ozon_sync_supply(supply, ozon, db)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неизвестный маркетплейс")
    result = await db.execute(_supply_query().where(FBOSupply.id == supply_id))
    supply = result.scalar_one()
    return _supply_to_out(supply)


@router.get("/supplies/{supply_id}/labels")
async def get_fbo_supply_labels(
    supply_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Download labels PDF for supply boxes."""
    supply = await _ensure_supply_access(supply_id, current_user, db)
    if supply.marketplace == "wb":
        wb = await get_wb_client(supply.company_id, db)
        ext_id = (supply.external_supply_id or "").strip()
        file_bytes = None
        media_type = "image/png"
        filename = "fbo_supply_barcode.png"
        if ext_id:
            file_bytes, media_type = await wb.get_supply_barcode(ext_id, "png")
            if file_bytes and ext_id:
                filename = f"wb_supply_{ext_id.replace('/', '_')}.png"
            if not file_bytes:
                stickers = await wb.get_supply_box_stickers(ext_id)
                if stickers:
                    import base64
                    for s in stickers:
                        f = s.get("file")
                        if f:
                            file_bytes = base64.b64decode(f)
                            break
        if not file_bytes:
            order_ids = []
            for box in supply.boxes:
                if box.barcode:
                    try:
                        order_ids.append(int(box.barcode))
                    except ValueError:
                        pass
            if order_ids:
                stickers = await wb.get_supply_stickers(order_ids)
                if stickers:
                    import base64
                    for s in stickers:
                        f = s.get("file")
                        if f:
                            file_bytes = base64.b64decode(f)
                            break
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Этикетки WB не получены (синхронизируйте поставку и повторите или дождитесь передачи в доставку)",
            )
        return StreamingResponse(
            iter([file_bytes]),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    if supply.marketplace == "ozon":
        ozon = await get_ozon_client(supply.company_id, db)
        ext_id = supply.external_supply_id
        if not ext_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Поставка ещё не синхронизирована с Ozon")
        try:
            supply_id_int = int(ext_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Некорректный external_supply_id")
        cargo_ids = [b.external_box_id for b in supply.boxes if b.external_box_id]
        if not cargo_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет идентификаторов грузомест (external_box_id) для этикеток Ozon")
        pdf_bytes = await ozon.get_supply_labels(supply_id_int, cargo_ids)
        if not pdf_bytes:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Этикетки не получены")
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=fbo_labels.pdf"},
        )
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неизвестный маркетплейс")


@router.post("/supplies/{supply_id}/import-barcodes", response_model=FBOSupplyOut)
async def import_fbo_barcodes(
  supply_id: int,
  payload: FBOBarcodeImport,
  db: AsyncSession = Depends(get_db),
  current_user: User = Depends(get_current_user),
) -> FBOSupplyOut:
    """Import barcodes for boxes (box_number -> barcode)."""
    supply = await _ensure_supply_access(supply_id, current_user, db)
    for box in supply.boxes:
        if box.box_number in payload.barcodes:
            box.barcode = payload.barcodes[box.box_number].strip() or None
    await db.commit()
    result = await db.execute(_supply_query().where(FBOSupply.id == supply_id))
    supply = result.scalar_one()
    return _supply_to_out(supply)
