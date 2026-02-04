"""Admin endpoints."""
from fastapi import APIRouter, Depends, File, HTTPException, Query, status, UploadFile
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_roles
from app.core.logging import logger
from app.db.models.contract_template import ContractTemplate
from app.db.models.document_chunk import DocumentChunk
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.admin import AdminUserOut, RoleUpdate
from app.schemas.contract_template import (
    ContractTemplateCreate,
    ContractTemplateOut,
    ContractTemplateUpdate,
)
from app.services.document_processor import (
    MAX_DOCUMENT_SIZE_BYTES,
    index_document,
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
    current_user: User = Depends(require_roles("admin")),
) -> dict:
    """Update user role."""
    if payload.role not in {"client", "warehouse", "admin"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.role = payload.role
    logger.info("role_changed", target_user_id=user_id, new_role=payload.role, by_admin=current_user.id)
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


# ----- RAG documents (для AI) -----


@router.get("/documents")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> list[dict]:
    """Список документов в RAG: source_file, chunks_count, document_type, version."""
    q = (
        select(
            DocumentChunk.source_file,
            func.count(DocumentChunk.id).label("chunks_count"),
            func.max(DocumentChunk.document_type).label("document_type"),
            func.max(DocumentChunk.version).label("version"),
        )
        .where(DocumentChunk.source_file.isnot(None))
        .group_by(DocumentChunk.source_file)
        .order_by(DocumentChunk.source_file)
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "source_file": r.source_file,
            "chunks_count": r.chunks_count,
            "document_type": r.document_type or "",
            "version": r.version or 0,
        }
        for r in rows
    ]


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> dict:
    """
    Загрузить PDF или DOCX в RAG (парсинг, чанки, эмбеддинги).
    Ограничения: размер до 15 MB, до 80 чанков. Любая ошибка возвращает 503 без падения воркера.
    """
    try:
        content = await file.read()
    except Exception as e:
        logger.exception("document_upload_read_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось прочитать файл",
        ) from e
    if len(content) > MAX_DOCUMENT_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Файл слишком большой. Максимум {MAX_DOCUMENT_SIZE_BYTES // (1024*1024)} MB",
        )
    name = (file.filename or "document").strip() or "document"
    if name.lower().endswith(".pdf"):
        document_type = "pdf"
    elif name.lower().endswith(".docx"):
        document_type = "docx"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только PDF и DOCX",
        )
    try:
        chunks_added = await index_document(db, name, content, document_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception(
            "document_index_failed",
            source_file=name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ошибка обработки документа. Попробуйте меньший файл или позже.",
        ) from e
    return {"source_file": name, "chunks_added": chunks_added}


@router.delete("/documents/{source_file:path}")
async def delete_document(
    source_file: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> dict:
    """Удалить все чанки документа по имени файла."""
    await db.execute(delete(DocumentChunk).where(DocumentChunk.source_file == source_file))
    await db.commit()
    return {"status": "ok"}
