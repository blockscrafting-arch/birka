"""RAG for project documentation."""
from sqlalchemy import select
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


async def build_rag_context_async(db: AsyncSession, message: str) -> str:
    """Build RAG context: use document chunks if available, else static."""
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
        result = await db.execute(
            select(DocumentChunk)
            .order_by(DocumentChunk.embedding.cosine_distance(embedding))
            .limit(3)
        )
        chunks = list(result.scalars().all())
        if not chunks:
            return build_rag_context(message)
        context = "\n\n".join(c.content for c in chunks)
        return f"{STATIC_BASE}\n\nКонтекст из документации:\n{context}\n\nВопрос клиента: {message}"
    except Exception:
        return build_rag_context(message)
