"""Add order_item_id to packing_records for per-line packing.

Revision ID: 0020_packing_record_order_item_id
Revises: 0019_order_item_destination
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = "0020_packing_record_order_item_id"
down_revision = "0019_order_item_destination"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "packing_records",
        sa.Column("order_item_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_packing_records_order_item_id",
        "packing_records",
        "order_items",
        ["order_item_id"],
        ["id"],
    )
    op.create_index(
        "ix_packing_records_order_item_id",
        "packing_records",
        ["order_item_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_packing_records_order_item_id", "packing_records")
    op.drop_constraint("fk_packing_records_order_item_id", "packing_records", type_="foreignkey")
    op.drop_column("packing_records", "order_item_id")
