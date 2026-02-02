"""Add document_chunks table for RAG.

Revision ID: 0008_document_chunks
Revises: 0007_order_completed_at
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa


revision = "0008_document_chunks"
down_revision = "0007_order_completed_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
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


def downgrade() -> None:
    op.drop_table("document_chunks")
