"""Add document_chunks table for RAG.

Revision ID: 0008_document_chunks
Revises: 0007_order_completed_at
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import NotSupportedError, OperationalError


revision = "0008_document_chunks"
down_revision = "0007_order_completed_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create pgvector extension and document_chunks table. Requires pgvector extension."""
    conn = op.get_bind()
    try:
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    except (NotSupportedError, OperationalError) as e:
        conn.rollback()
        raise RuntimeError(
            "pgvector extension is required for document_chunks. "
            "Install it (e.g. apt install postgresql-15-pgvector) or use a DB that has it."
        ) from e
    op.execute(
        sa.text(
            """
            CREATE TABLE document_chunks (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                source_file VARCHAR(256),
                chunk_index INTEGER DEFAULT 0,
                embedding vector(1536)
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS document_chunks"))
