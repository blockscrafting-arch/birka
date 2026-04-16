"""Add extended company fields from DaData.

Revision ID: 0009_company_extended_fields
Revises: 0008_document_chunks
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa


revision = "0009_company_extended_fields"
down_revision = "0008_document_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("kpp", sa.String(length=16), nullable=True))
    op.add_column("companies", sa.Column("ogrn", sa.String(length=20), nullable=True))
    op.add_column("companies", sa.Column("legal_address", sa.String(length=512), nullable=True))
    op.add_column("companies", sa.Column("okved", sa.String(length=16), nullable=True))
    op.add_column("companies", sa.Column("okved_name", sa.String(length=256), nullable=True))
    op.add_column("companies", sa.Column("bank_name", sa.String(length=256), nullable=True))
    op.add_column("companies", sa.Column("bank_corr_account", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "bank_corr_account")
    op.drop_column("companies", "bank_name")
    op.drop_column("companies", "okved_name")
    op.drop_column("companies", "okved")
    op.drop_column("companies", "legal_address")
    op.drop_column("companies", "ogrn")
    op.drop_column("companies", "kpp")
