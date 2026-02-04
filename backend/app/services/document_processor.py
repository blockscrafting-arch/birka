"""Document processing for RAG: PDF/DOCX parsing, chunking, indexing."""
from datetime import datetime, timezone
from io import BytesIO

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.core.logging import logger
from app.db.models.document_chunk import DocumentChunk
from app.services.rag import get_embedding

# Ограничения, чтобы не ронять воркер при больших файлах и множестве эмбеддингов
MAX_DOCUMENT_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MAX_CHUNKS_PER_DOCUMENT = 80


def parse_pdf(content: bytes) -> str:
    """Extract text from PDF via PyMuPDF. Returns concatenated page text."""
    try:
        import fitz  # pymupdf

        doc = fitz.open(stream=content, filetype="pdf")
        parts = []
        for page in doc:
            parts.append(page.get_text())
        doc.close()
        return "\n\n".join(parts).strip()
    except Exception as exc:
        logger.exception("pdf_parse_failed", error=str(exc))
        raise


def parse_docx(content: bytes) -> str:
    """Extract text from DOCX. Returns concatenated paragraph text."""
    try:
        from docx import Document

        doc = Document(BytesIO(content))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(parts).strip()
    except Exception as exc:
        logger.exception("docx_parse_failed", error=str(exc))
        raise


def split_into_chunks(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[str]:
    """Split text into chunks with overlap. Tries to break at paragraph boundaries."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            # Prefer break at paragraph or line end
            search = text.rfind("\n\n", start, end + 1)
            if search > start:
                end = search + 2
            else:
                search = text.rfind("\n", start, end + 1)
                if search > start:
                    end = search + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start >= len(text):
            break
    return chunks


async def index_document(
    db: AsyncSession,
    file_name: str,
    content: bytes,
    document_type: str,
) -> int:
    """
    Parse document, chunk, generate embeddings, store in DB.
    Replaces existing chunks for the same source_file (versioning: next version).
    Returns number of chunks added.
    """
    source_file = (file_name or "document").strip() or "document"
    if document_type not in ("pdf", "docx"):
        raise ValueError("document_type must be 'pdf' or 'docx'")
    if len(content) > MAX_DOCUMENT_SIZE_BYTES:
        raise ValueError(
            f"Файл слишком большой (макс. {MAX_DOCUMENT_SIZE_BYTES // (1024*1024)} MB)"
        )

    if document_type == "pdf":
        text = parse_pdf(content)
    else:
        text = parse_docx(content)

    if not text:
        return 0

    chunks_text = split_into_chunks(text, chunk_size=1000, overlap=200)
    if not chunks_text:
        return 0
    if len(chunks_text) > MAX_CHUNKS_PER_DOCUMENT:
        raise ValueError(
            f"Слишком много фрагментов ({len(chunks_text)}). "
            f"Максимум {MAX_CHUNKS_PER_DOCUMENT}. Уменьшите размер документа."
        )

    # Next version for this source_file
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
            document_type=document_type,
            version=next_version,
        )
        db.add(chunk)
        count += 1

    await db.commit()
    logger.info(
        "document_indexed",
        source_file=source_file,
        document_type=document_type,
        version=next_version,
        chunks_added=count,
    )
    return count
