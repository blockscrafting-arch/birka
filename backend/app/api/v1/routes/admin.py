"""Admin endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_roles
from app.db.models.contract_template import ContractTemplate
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.admin import AdminUserOut, RoleUpdate
from app.schemas.contract_template import (
    ContractTemplateCreate,
    ContractTemplateOut,
    ContractTemplateUpdate,
)

router = APIRouter()


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> list[AdminUserOut]:
    """List users for admin with optional search by name, telegram_id, username."""
    query = select(User).order_by(User.created_at.desc())
    if search and (s := search.strip()):
        conditions = [
            User.first_name.ilike(f"%{s}%"),
            User.last_name.ilike(f"%{s}%"),
            User.telegram_username.ilike(f"%{s}%"),
        ]
        if s.isdigit():
            conditions.append(User.telegram_id == int(s))
        query = query.where(or_(*conditions))
    result = await db.execute(query)
    return list(result.scalars().all())


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    payload: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> dict:
    """Update user role."""
    if payload.role not in {"client", "warehouse", "admin"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.role = payload.role
    await db.commit()
    return {"status": "ok"}


@router.get("/contract-templates", response_model=list[ContractTemplateOut])
async def list_contract_templates(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> list[ContractTemplateOut]:
    """List contract templates."""
    result = await db.execute(select(ContractTemplate).order_by(ContractTemplate.created_at.desc()))
    return list(result.scalars().all())


@router.post("/contract-templates", response_model=ContractTemplateOut)
async def create_contract_template(
    payload: ContractTemplateCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> ContractTemplateOut:
    """Create contract template."""
    if payload.is_default:
        await db.execute(update(ContractTemplate).values(is_default=False))
    template = ContractTemplate(
        name=payload.name.strip(),
        html_content=payload.html_content,
        is_default=payload.is_default,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.patch("/contract-templates/{template_id}", response_model=ContractTemplateOut)
async def update_contract_template(
    template_id: int,
    payload: ContractTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> ContractTemplateOut:
    """Update contract template."""
    result = await db.execute(select(ContractTemplate).where(ContractTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_default"):
        await db.execute(update(ContractTemplate).values(is_default=False))
    for key, value in data.items():
        setattr(template, key, value)
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/contract-templates/{template_id}")
async def delete_contract_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> dict:
    """Delete contract template."""
    result = await db.execute(select(ContractTemplate).where(ContractTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    await db.delete(template)
    await db.commit()
    return {"status": "ok"}
