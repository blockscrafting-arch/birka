"""Add company_api_keys table.

Revision ID: 0005_company_api_keys
Revises: 0004_ozon_fields
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa


revision = "0005_company_api_keys"
down_revision = "0004_ozon_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("wb_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("ozon_client_id_encrypted", sa.Text(), nullable=True),
        sa.Column("ozon_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_company_api_keys_company_id", "company_api_keys", ["company_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_company_api_keys_company_id", table_name="company_api_keys")
    op.drop_table("company_api_keys")
