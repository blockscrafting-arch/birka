"""Add file fields to contract_templates for DOCX/PDF uploads.

Revision ID: 0014_contract_template_files
Revises: 0013_document_chunk_meta
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa


revision = "0014_contract_template_files"
down_revision = "0013_document_chunk_meta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contract_templates", sa.Column("file_key", sa.String(512), nullable=True))
    op.add_column("contract_templates", sa.Column("file_name", sa.String(255), nullable=True))
    op.add_column("contract_templates", sa.Column("file_type", sa.String(20), nullable=True))
    op.add_column("contract_templates", sa.Column("docx_key", sa.String(512), nullable=True))
    op.alter_column(
        "contract_templates",
        "html_content",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "contract_templates",
        "html_content",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.drop_column("contract_templates", "docx_key")
    op.drop_column("contract_templates", "file_type")
    op.drop_column("contract_templates", "file_name")
    op.drop_column("contract_templates", "file_key")
