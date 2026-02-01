"""Shipment request endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.logging import logger
from app.db.models.company import Company
from app.db.models.shipment_request import ShipmentRequest
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.shipping import ShipmentRequestCreate, ShipmentRequestList, ShipmentRequestOut
from app.schemas.shipping import ShipmentRequestStatusUpdate

router = APIRouter()


@router.post("", response_model=ShipmentRequestOut)
async def create_shipment_request(
    payload: ShipmentRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShipmentRequestOut:
    """Create shipment request."""
    company_result = await db.execute(
        select(Company).where(Company.id == payload.company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        request = ShipmentRequest(
            company_id=payload.company_id,
            destination_type=payload.destination_type,
            destination_comment=payload.destination_comment,
        )
        db.add(request)
        await db.commit()
        await db.refresh(request)
        return request
    except Exception as exc:
        await db.rollback()
        logger.exception("shipment_request_failed", company_id=payload.company_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Shipment request failed")


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
        raise HTTPException(status_code=404, detail="Company not found")
    base_query = select(ShipmentRequest).where(ShipmentRequest.company_id == company_id)
    total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = int(total_result.scalar_one())
    offset = (page - 1) * limit
    result = await db.execute(base_query.offset(offset).limit(limit))
    items = list(result.scalars().all())
    return ShipmentRequestList(items=items, total=total, page=page, limit=limit)


@router.patch("/{request_id}/status", response_model=ShipmentRequestOut)
async def update_shipment_status(
    request_id: int,
    payload: ShipmentRequestStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShipmentRequestOut:
    """Update shipment request status."""
    result = await db.execute(select(ShipmentRequest).where(ShipmentRequest.id == request_id))
    request = result.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Shipment request not found")
    if current_user.role not in {"warehouse", "admin"}:
        company_result = await db.execute(
            select(Company).where(Company.id == request.company_id, Company.user_id == current_user.id)
        )
        if not company_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Company not found")
    try:
        request.status = payload.status
        await db.commit()
        await db.refresh(request)
        return request
    except Exception as exc:
        await db.rollback()
        logger.exception("shipment_status_failed", request_id=request_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Shipment status update failed")
