"""Services (pricing) endpoints."""
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_roles
from app.core.logging import logger
from app.db.models.service import Service
from app.db.models.service_history import ServicePriceHistory
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.service import (
    CalculateRequest,
    CalculateResponse,
    CalculateItemOut,
    ServiceCreate,
    ServiceOut,
    ServicePriceHistoryOut,
    ServiceReorderRequest,
    ServiceUpdate,
)
from app.services.excel import export_services, parse_services_excel
from app.services.pdf import generate_price_list_pdf

router = APIRouter()


@router.get("", response_model=list[ServiceOut])
async def list_services(
    category: str | None = Query(None, description="Filter by category"),
    include_inactive: bool = Query(False, description="Include inactive (admin only)"),
    q: str | None = Query(None, description="Search in name, category, comment"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ServiceOut]:
    """List services, optionally filtered by category and search. Admins can pass include_inactive=True."""
    query = select(Service).order_by(
        Service.category.asc(), Service.sort_order.asc(), Service.name.asc()
    )
    if not include_inactive or current_user.role != "admin":
        query = query.where(Service.is_active.is_(True))
    if category and category.strip():
        query = query.where(Service.category == category.strip())
    term = (q or "").strip()
    if term:
        # Escape ILIKE wildcards so user input is literal (\% and \_ not treated as wildcards)
        escape_char = "\\"
        term_escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{term_escaped}%"
        query = query.where(
            or_(
                Service.name.ilike(pattern, escape=escape_char),
                Service.category.ilike(pattern, escape=escape_char),
                Service.comment.ilike(pattern, escape=escape_char),
            )
        )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/categories", response_model=list[str])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[str]:
    """List distinct service categories."""
    query = (
        select(Service.category)
        .where(Service.is_active.is_(True))
        .distinct()
        .order_by(Service.category.asc())
    )
    result = await db.execute(query)
    return [row[0] for row in result.all()]


@router.post("/calculate", response_model=CalculateResponse)
async def calculate_services(
    payload: CalculateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CalculateResponse:
    """Calculate total cost for a list of services and quantities."""
    ids = [item.service_id for item in payload.items]
    result = await db.execute(select(Service).where(Service.id.in_(ids), Service.is_active.is_(True)))
    services_by_id = {s.id: s for s in result.scalars().all()}
    items_out: list[CalculateItemOut] = []
    total = Decimal("0")
    for item in payload.items:
        service = services_by_id.get(item.service_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Услуга id={item.service_id} не найдена или неактивна",
            )
        subtotal = (Decimal(str(service.price)) * Decimal(str(item.quantity))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total += subtotal
        items_out.append(
            CalculateItemOut(
                service_id=service.id,
                name=service.name,
                category=service.category,
                price=service.price,
                unit=service.unit,
                quantity=item.quantity,
                subtotal=subtotal,
            )
        )
    total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return CalculateResponse(items=items_out, total=total)


@router.post("", response_model=ServiceOut)
async def create_service(
    payload: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> ServiceOut:
    """Create service (admin)."""
    service = Service(
        category=payload.category.strip(),
        name=payload.name.strip(),
        price=payload.price,
        unit=payload.unit.strip() or "шт",
        comment=payload.comment.strip() if payload.comment else None,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    logger.info("service_created", service_id=service.id, name=service.name, category=service.category)
    return service


@router.patch("/reorder", response_model=list[ServiceOut])
async def reorder_services(
    payload: ServiceReorderRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> list[ServiceOut]:
    """Update sort_order for multiple services (admin)."""
    ids = [item.id for item in payload.items]
    result = await db.execute(select(Service).where(Service.id.in_(ids)))
    services_by_id = {s.id: s for s in result.scalars().all()}
    if len(services_by_id) != len(ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more service ids not found")
    for item in payload.items:
        services_by_id[item.id].sort_order = item.sort_order
    await db.commit()
    ordered = [services_by_id[item.id] for item in payload.items]
    for s in ordered:
        await db.refresh(s)
    return ordered


@router.patch("/{service_id}", response_model=ServiceOut)
async def update_service(
    service_id: int,
    payload: ServiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
) -> ServiceOut:
    """Update service (admin). Records price change in history when price changes."""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Услуга не найдена")
    dump = payload.model_dump(exclude_unset=True)
    if "price" in dump and dump["price"] is not None and dump["price"] != service.price:
        db.add(
            ServicePriceHistory(
                service_id=service.id,
                old_price=service.price,
                new_price=dump["price"],
                changed_by_user_id=current_user.id,
            )
        )
    for key, value in dump.items():
        if key in ("category", "name", "comment", "unit") and isinstance(value, str):
            value = value.strip() if value else None
            if key in ("category", "name", "unit") and not value:
                continue
        setattr(service, key, value)
    await db.commit()
    await db.refresh(service)
    logger.info("service_updated", service_id=service.id, fields=list(dump.keys()))
    return service


@router.get("/{service_id}/history", response_model=list[ServicePriceHistoryOut])
async def get_service_price_history(
    service_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> list[ServicePriceHistoryOut]:
    """List price change history for a service (admin)."""
    result = await db.execute(
        select(ServicePriceHistory)
        .where(ServicePriceHistory.service_id == service_id)
        .order_by(ServicePriceHistory.changed_at.desc())
    )
    return list(result.scalars().all())


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> None:
    """Soft-delete service (admin): set is_active=False."""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Услуга не найдена")
    service.is_active = False
    await db.commit()
    logger.info("service_deactivated", service_id=service_id)


@router.post("/import", response_model=dict)
async def import_services(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> dict:
    """Import services from Excel file (admin). Columns: Категория, Название, Цена, Ед., Комментарий."""
    file_bytes = await file.read()
    try:
        rows = parse_services_excel(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    created = 0
    updated = 0
    for row in rows:
        cat = row["category"]
        name = row["name"]
        price = Decimal(str(row["price"]))
        unit = row.get("unit", "шт")
        comment = row.get("comment")
        existing = await db.execute(
            select(Service).where(Service.category == cat, Service.name == name)
        )
        service = existing.scalar_one_or_none()
        if service:
            service.price = price
            service.unit = unit
            service.comment = comment
            updated += 1
        else:
            db.add(
                Service(
                    category=cat,
                    name=name,
                    price=price,
                    unit=unit,
                    comment=comment,
                    is_active=True,
                )
            )
            created += 1
    await db.commit()
    logger.info("services_imported", created=created, updated=updated)
    return {"created": created, "updated": updated}


@router.get("/export")
async def export_services_excel(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> Response:
    """Export all (including inactive) services to Excel (admin)."""
    result = await db.execute(
        select(Service).order_by(Service.category.asc(), Service.sort_order.asc(), Service.name.asc())
    )
    services = list(result.scalars().all())
    buffer = export_services(services)
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=services.xlsx"},
    )


@router.get("/pdf")
async def export_services_pdf(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Response:
    """Export active services as PDF price list."""
    result = await db.execute(
        select(Service)
        .where(Service.is_active.is_(True))
        .order_by(Service.category.asc(), Service.sort_order.asc(), Service.name.asc())
    )
    services = list(result.scalars().all())
    pdf_bytes = generate_price_list_pdf(services)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=prajs-birka.pdf"},
    )
