"""Add destination to order_items for per-line warehouse/ship-to.

Revision ID: 0019_order_item_destination
Revises: 0018_fbo_supplies
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = "0019_order_item_destination"
down_revision = "0018_fbo_supplies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_items",
        sa.Column("destination", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("order_items", "destination")
