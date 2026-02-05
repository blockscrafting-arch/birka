"""RAG for project documentation."""
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.core.config import settings
from app.db.models.document_chunk import DocumentChunk

STATIC_BASE = (
    "Ты помощник фулфилмент компании Бирка. "
    "Отвечай кратко и по делу, используй статусы заявок: "
    "На приемке, Принято, Упаковка, Готово к отгрузке, Завершено. "
    "Если вопрос о браке — напомни, что фото обязательны."
)


def build_rag_context(message: str) -> str:
    """Build RAG context from static instructions (sync fallback)."""
    if not settings.OPENAI_API_KEY:
        return ""
    return f"{STATIC_BASE}\nВопрос клиента: {message}"


async def get_embedding(text: str) -> list[float] | None:
    """Get embedding for text via OpenAI. Returns None if no API key."""
    if not settings.OPENAI_API_KEY or not text.strip():
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.embeddings.create(model="text-embedding-3-small", input=text.strip())
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
        )
        db.add(chunk)
        count += 1

    await db.commit()
    return count


def _marketplace_filter_from_message(message: str) -> str | None:
    """Infer marketplace filter from user message. Returns source_file pattern or None for no filter."""
    msg = (message or "").lower()
    if "wb" in msg or "wildberries" in msg or "вб" in msg or "вайлдберриз" in msg:
        return "wb"
    if "ozon" in msg or "озон" in msg:
        return "ozon"
    return None


async def build_rag_context_async(db: AsyncSession, message: str) -> str:
    """Build RAG context: use document chunks if available, else static.
    When message mentions a marketplace (WB/Ozon), prefer chunks from that marketplace's docs (source_file).
    """
    if not settings.OPENAI_API_KEY:
        return build_rag_context(message)
    try:
        count_result = await db.execute(select(func.count()).select_from(DocumentChunk))
        if int(count_result.scalar_one()) == 0:
            return build_rag_context(message)
    except Exception:
        return build_rag_context(message)
    embedding = await get_embedding(message)
    if not embedding:
        return build_rag_context(message)
    try:
        base_q = select(DocumentChunk).order_by(DocumentChunk.embedding.cosine_distance(embedding))
        mf = _marketplace_filter_from_message(message)
        if mf == "wb":
            base_q = base_q.where(DocumentChunk.source_file.ilike("%wb%"))
        elif mf == "ozon":
            base_q = base_q.where(DocumentChunk.source_file.ilike("%ozon%"))
        result = await db.execute(base_q.limit(3))
        chunks = list(result.scalars().all())
        if not chunks and mf:
            result = await db.execute(
                select(DocumentChunk).order_by(DocumentChunk.embedding.cosine_distance(embedding)).limit(3)
            )
            chunks = list(result.scalars().all())
        if not chunks:
            return build_rag_context(message)
        context = "\n\n".join(c.content for c in chunks)
        return f"{STATIC_BASE}\n\nКонтекст из документации:\n{context}\n\nВопрос клиента: {message}"
    except Exception:
        return build_rag_context(message)
