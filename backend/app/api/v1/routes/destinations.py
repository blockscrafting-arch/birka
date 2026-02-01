"""Destination (address) endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_roles
from app.db.models.destination import Destination
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.destination import DestinationCreate, DestinationOut, DestinationUpdate

router = APIRouter()


@router.get("", response_model=list[DestinationOut])
async def list_destinations(
    active_only: bool = Query(True, description="Only active destinations"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[DestinationOut]:
    """List destinations (for order form)."""
    query = select(Destination).order_by(Destination.name.asc())
    if active_only:
        query = query.where(Destination.is_active.is_(True))
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=DestinationOut)
async def create_destination(
    payload: DestinationCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> DestinationOut:
    """Create destination (admin)."""
    dest = Destination(name=payload.name.strip(), is_active=True)
    db.add(dest)
    await db.commit()
    await db.refresh(dest)
    return dest


@router.patch("/{destination_id}", response_model=DestinationOut)
async def update_destination(
    destination_id: int,
    payload: DestinationUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> DestinationOut:
    """Update destination (admin)."""
    result = await db.execute(select(Destination).where(Destination.id == destination_id))
    dest = result.scalar_one_or_none()
    if not dest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(dest, key, value)
    await db.commit()
    await db.refresh(dest)
    return dest


@router.delete("/{destination_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_destination(
    destination_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> None:
    """Soft-delete destination (admin): set is_active=False."""
    result = await db.execute(select(Destination).where(Destination.id == destination_id))
    dest = result.scalar_one_or_none()
    if not dest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found")
    dest.is_active = False
    await db.commit()
