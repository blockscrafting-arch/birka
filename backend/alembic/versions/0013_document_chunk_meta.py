"""Add created_at, document_type, version to document_chunks.

Revision ID: 0013_document_chunk_meta
Revises: 0012_order_services
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa


revision = "0013_document_chunk_meta"
down_revision = "0012_order_services"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.add_column("document_chunks", sa.Column("document_type", sa.String(20), nullable=True))
    op.add_column("document_chunks", sa.Column("version", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_chunks", "version")
    op.drop_column("document_chunks", "document_type")
    op.drop_column("document_chunks", "created_at")
