"""Add Ozon fields to products.

Revision ID: 0004_ozon_fields
Revises: 0003_order_counters
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa


revision = "0004_ozon_fields"
down_revision = "0003_order_counters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("ozon_article", sa.String(length=64), nullable=True))
    op.add_column("products", sa.Column("ozon_url", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "ozon_url")
    op.drop_column("products", "ozon_article")
