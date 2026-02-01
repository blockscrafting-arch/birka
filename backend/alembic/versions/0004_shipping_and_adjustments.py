"""Add shipment requests and product supplier.

Revision ID: 0004_shipping_and_adjustments
Revises: 0003_order_counters
Create Date: 2026-02-01
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_shipping_and_adjustments"
down_revision = "0003_order_counters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("supplier_name", sa.String(length=256), nullable=True))
    op.add_column(
        "order_photos",
        sa.Column("product_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_order_photos_product_id", "order_photos", ["product_id"])
    op.create_foreign_key(
        "fk_order_photos_product_id",
        "order_photos",
        "products",
        ["product_id"],
        ["id"],
    )
    op.add_column(
        "order_items",
        sa.Column("adjustment_qty", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "order_items",
        sa.Column("adjustment_note", sa.String(length=256), nullable=True),
    )
    op.create_table(
        "shipment_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("destination_type", sa.String(length=32), nullable=False),
        sa.Column("destination_comment", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="Создано"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
    op.create_index("ix_shipment_requests_company_id", "shipment_requests", ["company_id"])
    op.create_index("ix_shipment_requests_status", "shipment_requests", ["status"])


def downgrade() -> None:
    op.drop_constraint("fk_order_photos_product_id", "order_photos", type_="foreignkey")
    op.drop_index("ix_order_photos_product_id", table_name="order_photos")
    op.drop_column("order_photos", "product_id")
    op.drop_index("ix_shipment_requests_status", table_name="shipment_requests")
    op.drop_index("ix_shipment_requests_company_id", table_name="shipment_requests")
    op.drop_table("shipment_requests")
    op.drop_column("order_items", "adjustment_note")
    op.drop_column("order_items", "adjustment_qty")
    op.drop_column("products", "supplier_name")
