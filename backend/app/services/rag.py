"""RAG for project documentation."""
from datetime import datetime, timezone

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.core.config import settings
from app.core.db_utils import escape_ilike
from app.db.models.document_chunk import DocumentChunk
from app.services.rag_intent import SECTION_INTENTS, detect_rag_intent

# Ключевые слова по интенту для гибридного поиска (ILIKE по content)
HYBRID_INTENT_KEYWORDS: dict[str, list[str]] = {
    "obuv": ["обув", "силикагель", "50 мкм", "мешочк", "зип-застёжк"],
    "zerkala": ["зеркал", "уголк", "пузырчат", "хрупк", "гофрокартон"],
    "posuda": ["посуда", "пузырчат", "хрупк", "2 слоя"],
}

# Дополнительные инструкции при наличии контекста из документации (без дублирования идентичности из system prompt)
STATIC_BASE = (
    "Используй статусы заявок: На приемке, Принято, Упаковка, Готово к отгрузке, Завершено. "
    "При вопросе о браке напомни, что фото обязательны."
)

# Жёсткое правило: по упаковке и требованиям маркетплейсов отвечать ТОЛЬКО по переданному контексту
RAG_STRICT_INSTRUCTION = (
    "Отвечай СТРОГО только на основе приведённого ниже контекста из документации. "
    "Не используй собственные знания об упаковке и требованиях WB/Ozon. "
    "Один запрос — один ответ: отвечай ТОЛЬКО на последний вопрос пользователя. "
    "ЗАПРЕЩЕНО добавлять в ответ блоки про другие темы: если спросили про габариты — не пиши про посуду или обувь; если спросили про этикетку Ozon — не пиши про обувь на ВБ; если спросили про обувь — не добавляй блок про зеркала, и наоборот. Один тематический блок в ответе. "
    "Не пиши фразы вида «по вопросу об … в документации нет информации» про другие сообщения из чата — только ответ на текущий вопрос. "
    "Для Ozon: в контексте нет размеров этикеток (58×40, 120×75 и т.д.), запрета красного скотча, правил по зеркалам. Если спрашивают про это и в контексте нет — напиши только: «В загруженной документации нет информации по этому вопросу.» Не называй цифры и правила от себя. "
    "Если ответа на вопрос в контексте нет — напиши только: «В загруженной документации нет информации по этому вопросу.»"
)


def build_rag_context(message: str) -> str:
    """Build RAG context from static instructions (sync fallback). Returns empty string if no API key."""
    if not settings.OPENAI_API_KEY:
        return ""
    return f"{STATIC_BASE}\nВопрос клиента: {message}"


async def get_embedding(text: str) -> list[float] | None:
    """Get embedding for text via OpenAI (async). Returns None if no API key."""
    if not settings.OPENAI_API_KEY or not text.strip():
        return None
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.embeddings.create(model="text-embedding-3-small", input=text.strip())
        return resp.data[0].embedding
    except Exception:
        return None


def _split_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into chunks with overlap (simple paragraph-aware splitter)."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            split_at = text.rfind("\n\n", start, end + 1)
            if split_at > start:
                end = split_at + 2
            else:
                split_at = text.rfind("\n", start, end + 1)
                if split_at > start:
                    end = split_at + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start >= len(text):
            break
    return chunks


async def upload_document_to_rag(db: AsyncSession, content: str, name: str) -> int:
    """Upload plain text content into document_chunks with embeddings."""
    source_file = (name or "document").strip() or "document"
    chunks_text = _split_text(content, chunk_size=1000, overlap=200)
    if not chunks_text:
        return 0

    version_result = await db.execute(
        select(func.coalesce(func.max(DocumentChunk.version), 0)).where(
            DocumentChunk.source_file == source_file
        )
    )
    next_version = int(version_result.scalar_one() or 0) + 1

    await db.execute(delete(DocumentChunk).where(DocumentChunk.source_file == source_file))

    now = datetime.now(timezone.utc)
    section = _section_for_source_file(source_file)
    count = 0
    for i, chunk_content in enumerate(chunks_text):
        embedding = await get_embedding(chunk_content)
        if not embedding:
            continue
        chunk = DocumentChunk(
            content=chunk_content,
            source_file=source_file,
            chunk_index=i,
            embedding=embedding,
            created_at=now,
            document_type="txt",
            version=next_version,
            section=section,
        )
        db.add(chunk)
        count += 1

    await db.commit()
    return count


def _section_for_source_file(name: str) -> str | None:
    """Infer section for txt/rtf by filename (wb -> wb_common, ozon -> ozon_common). Used in upload_document_to_rag."""
    lower = (name or "").lower()
    if "wb" in lower or "wildberries" in lower:
        return "wb_common"
    if "ozon" in lower:
        return "ozon_common"
    return None


def _marketplace_filter_from_message(message: str) -> str | None:
    """Infer marketplace filter from user message. Returns source_file pattern or None for no filter."""
    msg = (message or "").lower()
    if "wb" in msg or "wildberries" in msg or "вб" in msg or "вайлдберриз" in msg:
        return "wb"
    if "ozon" in msg or "озон" in msg:
        return "ozon"
    return None


def _query_for_embedding(message: str) -> str:
    """Query text for embedding: original message or neutral prefix for short packaging queries (no category keywords)."""
    msg = (message or "").strip()
    if not msg:
        return msg
    lower = msg.lower()
    if len(msg) < 50 and any(w in lower for w in ("упаковк", "вб", "wb", "озон", "ozon")):
        if "вб" in lower or "wb" in lower or "wildberries" in lower:
            return f"Требования упаковки. {msg} Wildberries."
        if "озон" in lower or "ozon" in lower:
            return f"Требования упаковки. {msg} Ozon."
        return f"Требования упаковки. {msg}"
    return msg


async def build_rag_context_async(db: AsyncSession, message: str) -> tuple[str | None, str]:
    """Build RAG context: use document chunks if available.
    Returns (rag_system_content, user_message). rag_system_content is None when no chunks;
    then user_message is the raw message. When chunks exist, rag_system_content is the doc context
    to add as a separate system message; user_message is the raw message.
    Uses intent to filter by section (obuv/zerkala/posuda for WB DOCX) and marketplace (source_file).
    """
    if not settings.OPENAI_API_KEY:
        return (None, message)
    try:
        count_result = await db.execute(select(func.count()).select_from(DocumentChunk))
        if int(count_result.scalar_one()) == 0:
            return (None, message)
    except Exception:
        return (None, message)
    query_for_embedding = _query_for_embedding(message)
    embedding = await get_embedding(query_for_embedding)
    if not embedding:
        return (None, message)
    intent = detect_rag_intent(message)
    mf = _marketplace_filter_from_message(message)
    try:
        base_q = select(DocumentChunk).order_by(DocumentChunk.embedding.cosine_distance(embedding))
        if mf == "wb":
            base_q = base_q.where(
                or_(
                    DocumentChunk.source_file.ilike("%wb%"),
                    DocumentChunk.source_file.ilike("%разные_виды%"),
                )
            )
            if intent in ("obuv", "zerkala", "posuda"):
                base_q = base_q.where(DocumentChunk.section == intent)
            elif intent in ("gabarity_wb", "strejch_skotch_wb"):
                base_q = base_q.where(
                    or_(
                        DocumentChunk.section == "wb_common",
                        DocumentChunk.section.is_(None),
                    )
                )
        elif mf == "ozon":
            base_q = base_q.where(DocumentChunk.source_file.ilike("%ozon%"))
        limit = max(1, settings.RAG_CHUNKS_LIMIT)
        result = await db.execute(base_q.limit(limit))
        chunks = list(result.scalars().all())
        if not chunks and mf and intent and intent in SECTION_INTENTS:
            base_q_fallback = (
                select(DocumentChunk)
                .order_by(DocumentChunk.embedding.cosine_distance(embedding))
                .where(
                    or_(
                        DocumentChunk.source_file.ilike("%wb%"),
                        DocumentChunk.source_file.ilike("%разные_виды%"),
                    )
                    if mf == "wb"
                    else DocumentChunk.source_file.ilike("%ozon%")
                )
            )
            result = await db.execute(base_q_fallback.limit(limit))
            chunks = list(result.scalars().all())
        if not chunks:
            return (None, message)
        # Гибрид: добираем чанки по ключевым словам (obuv/zerkala/posuda), которых ещё нет в выборке
        if (
            settings.RAG_HYBRID_KEYWORD_BOOST
            and intent in ("obuv", "zerkala", "posuda")
            and mf == "wb"
            and intent in HYBRID_INTENT_KEYWORDS
        ):
            hybrid_max = settings.RAG_HYBRID_KEYWORD_CHUNKS_MAX
            if hybrid_max > 0:
                kw_list = HYBRID_INTENT_KEYWORDS[intent]
                keyword_conditions = or_(
                    *[
                        DocumentChunk.content.ilike(f"%{escape_ilike(kw)}%", escape="\\")
                        for kw in kw_list
                    ]
                )
                hybrid_q = (
                    select(DocumentChunk)
                    .where(
                        or_(
                            DocumentChunk.source_file.ilike("%wb%"),
                            DocumentChunk.source_file.ilike("%разные_виды%"),
                        )
                    )
                    .where(DocumentChunk.section == intent)
                    .where(keyword_conditions)
                )
                existing_ids = [c.id for c in chunks]
                if existing_ids:
                    hybrid_q = hybrid_q.where(DocumentChunk.id.notin_(existing_ids))
                hybrid_q = hybrid_q.limit(hybrid_max)
                hybrid_result = await db.execute(hybrid_q)
                extra_chunks = list(hybrid_result.scalars().all())
                chunks = chunks + extra_chunks
        chunks = chunks[:limit]
        context = "\n\n".join(c.content for c in chunks)
        rag_system = (
            f"{STATIC_BASE}\n\n{RAG_STRICT_INSTRUCTION}\n\n"
            f"Контекст из документации:\n{context}"
        )
        return (rag_system, message)
    except Exception:
        return (None, message)
