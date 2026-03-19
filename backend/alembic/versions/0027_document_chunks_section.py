"""Add section column to document_chunks for RAG section filtering.

Revision ID: 0027_document_chunks_section
Revises: 0026_barcode_scan_log
Create Date: 2026-02-20

"""
from alembic import op
import sqlalchemy as sa


revision = "0027_document_chunks_section"
down_revision = "0026_barcode_scan_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column("section", sa.String(128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_chunks", "section")
