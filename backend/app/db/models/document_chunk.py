"""Document chunk model for RAG."""
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.db.base import Base

VECTOR_DIM = 1536  # OpenAI text-embedding-3-small


class DocumentChunk(Base):
    """Chunk of document with embedding for RAG retrieval."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_file: Mapped[str | None] = mapped_column(String(256))
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[list | None] = mapped_column(Vector(VECTOR_DIM), nullable=True)
