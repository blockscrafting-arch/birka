"""Admin endpoints."""
import asyncio
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, status, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_roles
from app.core.logging import logger
from app.db.models.contract_template import ContractTemplate
from app.db.models.document_chunk import DocumentChunk
from app.db.models.service import Service
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.admin import AdminUserOut, RoleUpdate
from app.schemas.contract_template import (
    ContractTemplateCreate,
    ContractTemplateOut,
    ContractTemplateUpdate,
)
from app.services.contract_template_service import (
    delete_template_files,
    head_check_upload,
    upload_template_file,
    validate_template_upload,
)
from app.services.document_processor import (
    MAX_DOCUMENT_SIZE_BYTES,
    index_document,
)
from app.services.rag import upload_document_to_rag
from app.services.files import content_disposition
from app.services.s3 import S3Service

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
    """Create contract template (legacy HTML)."""
    if payload.is_default:
        await db.execute(update(ContractTemplate).values(is_default=False))
    template = ContractTemplate(
        name=payload.name.strip(),
        html_content=payload.html_content,
        is_default=payload.is_default,
    )
    db.add(template)
    try:
        await db.commit()
        await db.refresh(template)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Другой шаблон уже выбран по умолчанию. Повторите попытку.",
        ) from None
    return template


@router.post("/contract-templates/upload", response_model=ContractTemplateOut)
async def upload_contract_template(
    file: UploadFile = File(...),
    name: str = Form(..., min_length=1),
    is_default: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> ContractTemplateOut:
    """
    Upload DOCX or RTF as contract template. RTF is converted to DOCX when generating the contract.
    """
    try:
        content = await file.read()
    except Exception as e:
        logger.exception("contract_template_upload_read_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось прочитать файл",
        ) from e
    filename = (file.filename or "document").strip() or "document"
    file_type, err = validate_template_upload(content, filename)
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    s3 = S3Service()
    try:
        file_key, docx_key = await asyncio.to_thread(
            upload_template_file, s3, content, filename, file_type
        )
    except Exception as e:
        logger.exception("contract_template_upload_s3_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ошибка загрузки файла. Попробуйте позже.",
        ) from e

    ok_file = await head_check_upload(s3, file_key)
    ok_docx = True
    if docx_key:
        ok_docx = await head_check_upload(s3, docx_key)
    if not ok_file or not ok_docx:
        delete_template_files(s3, file_key, docx_key)
        logger.warning("contract_template_head_check_failed", file_key=file_key, docx_key=docx_key)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Файл загружен, но недоступен по URL. Проверьте настройки S3 и FILE_PUBLIC_BASE_URL.",
        )

    if is_default:
        await db.execute(update(ContractTemplate).values(is_default=False))
    template = ContractTemplate(
        name=name.strip(),
        html_content=None,
        is_default=is_default,
        file_key=file_key,
        file_name=filename,
        file_type=file_type,
        docx_key=docx_key,
    )
    db.add(template)
    try:
        await db.commit()
        await db.refresh(template)
    except IntegrityError:
        await db.rollback()
        delete_template_files(s3, file_key, docx_key)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Другой шаблон уже выбран по умолчанию. Повторите попытку.",
        ) from None
    return template


def _stream_s3_chunks(s3: S3Service, key: str):
    """Sync generator: yields chunks from S3. Used from thread for streaming download."""
    yield from s3.stream_chunks(key)


@router.get("/contract-templates/{template_id}/download")
async def download_contract_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """Download original template file (DOCX or PDF) from S3 (streamed, no full load in memory)."""
    result = await db.execute(select(ContractTemplate).where(ContractTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template or not template.file_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template or file not found")
    s3 = S3Service()

    async def chunk_iter():
        try:
            gen = await asyncio.to_thread(_stream_s3_chunks, s3, template.file_key)
        except Exception as e:
            logger.exception("contract_template_download_failed", template_id=template_id, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Не удалось скачать файл"
            ) from e
        while True:
            chunk = await asyncio.to_thread(next, gen, None)
            if chunk is None:
                break
            yield chunk

    ft = (template.file_type or "").lower()
    if ft == "pdf":
        media_type = "application/pdf"
    elif ft == "rtf":
        media_type = "application/rtf"
    else:
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    filename = template.file_name or "template"
    return StreamingResponse(
        chunk_iter(),
        media_type=media_type,
        headers={"Content-Disposition": content_disposition(filename)},
    )


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
    try:
        await db.commit()
        await db.refresh(template)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Другой шаблон уже выбран по умолчанию. Повторите попытку.",
        ) from None
    return template


@router.delete("/contract-templates/{template_id}")
async def delete_contract_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> dict:
    """Delete contract template and its files from S3 if file-based."""
    result = await db.execute(select(ContractTemplate).where(ContractTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    if template.file_key:
        s3 = S3Service()
        delete_template_files(s3, template.file_key, template.docx_key)
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
    Загрузить DOCX или TXT в RAG (парсинг, чанки, эмбеддинги).
    Ограничения: размер до 15 MB, до 80 чанков. TXT — UTF-8.
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
    raw_name = (file.filename or "document").strip() or "document"
    name = raw_name.replace("\\", "/").split("/")[-1] or "document"
    if name.lower().endswith(".docx"):
        document_type = "docx"
    elif name.lower().endswith(".txt"):
        document_type = "txt"
    elif name.lower().endswith(".rtf"):
        document_type = "rtf"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только DOCX, TXT и RTF",
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


# ----- RAG seed (прайс + документы из docs/rag) -----


def _resolve_rag_dir() -> Path | None:
    """Папка с .txt для RAG (в контейнере /docs/rag)."""
    env_path = os.getenv("DOCS_RAG_PATH")
    if env_path:
        p = Path(env_path).expanduser()
        if p.is_dir():
            return p
    for candidate in [Path("/docs/rag"), Path("/app/docs/rag")]:
        if candidate.is_dir():
            return candidate
    return None


@router.post("/rag/seed")
async def rag_seed(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> dict:
    """Заполнить RAG: загрузить .txt из docs/rag и опционально синхронизировать прайс услуг."""
    rag_dir = _resolve_rag_dir()
    if not rag_dir:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Папка docs/rag не найдена (DOCS_RAG_PATH или /docs/rag)",
        )
    files = sorted(rag_dir.glob("*.txt"))
    total = 0
    for path in files:
        try:
            content = path.read_text(encoding="utf-8")
            count = await upload_document_to_rag(db, content, path.name)
            total += count
        except Exception as e:
            logger.warning("rag_seed_file_failed", path=str(path), error=str(e))
    return {"status": "ok", "files_processed": len(files), "chunks_added": total}


SERVICES_RAG_SOURCE = "services_price.txt"


@router.post("/rag/sync-services")
async def rag_sync_services(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> dict:
    """Синхронизация прайса услуг в RAG: выгрузка активных услуг в текст и индексация."""
    result = await db.execute(
        select(Service)
        .where(Service.is_active.is_(True))
        .order_by(Service.category, Service.sort_order, Service.id)
    )
    services = list(result.scalars().all())
    lines = ["Прайс услуг Бирка (фулфилмент).", ""]
    for s in services:
        parts = [f"Услуга: {s.name}. Категория: {s.category}. Цена: {s.price} {s.unit}."]
        if s.comment and s.comment.strip():
            parts.append(f" Комментарий: {s.comment.strip()}.")
        lines.append(" ".join(parts))
    content = "\n".join(lines)
    if not content.strip():
        return {"status": "ok", "message": "no active services", "chunks_added": 0}
    chunks_added = await upload_document_to_rag(db, content, SERVICES_RAG_SOURCE)
    logger.info("rag_sync_services_done", services_count=len(services), chunks_added=chunks_added)
    return {"status": "ok", "chunks_added": chunks_added}
