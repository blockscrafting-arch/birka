"""Add CASCADE DELETE on order_photos and packing_records FK to orders.

Revision ID: 0030_cascade_order_photo_packing
Revises: 0029_fk_cascades
Create Date: 2026-04-09

"""
from alembic import op

revision = "0030_cascade_order_photo_packing"
down_revision = "0029_fk_cascades"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # order_photos.order_id — add CASCADE DELETE
    op.drop_constraint("order_photos_order_id_fkey", "order_photos", type_="foreignkey")
    op.create_foreign_key(
        "order_photos_order_id_fkey",
        "order_photos",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # packing_records.order_id — add CASCADE DELETE
    op.drop_constraint("packing_records_order_id_fkey", "packing_records", type_="foreignkey")
    op.create_foreign_key(
        "packing_records_order_id_fkey",
        "packing_records",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("packing_records_order_id_fkey", "packing_records", type_="foreignkey")
    op.create_foreign_key(
        "packing_records_order_id_fkey", "packing_records", "orders", ["order_id"], ["id"]
    )

    op.drop_constraint("order_photos_order_id_fkey", "order_photos", type_="foreignkey")
    op.create_foreign_key(
        "order_photos_order_id_fkey", "order_photos", "orders", ["order_id"], ["id"]
    )
