"""Add company_api_keys for WB/Ozon API keys per company.

Revision ID: 0021_company_api_keys
Revises: 0020_packing_record_order_item_id
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = "0021_company_api_keys"
down_revision = "0020_packing_record_order_item_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("wb_api_key", sa.String(length=512), nullable=True),
        sa.Column("ozon_client_id", sa.String(length=128), nullable=True),
        sa.Column("ozon_api_key", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_company_api_keys_company_id", "company_api_keys", ["company_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_company_api_keys_company_id", table_name="company_api_keys")
    op.drop_table("company_api_keys")
