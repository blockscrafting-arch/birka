"""Extend shipment_requests: order_id, warehouse_name, delivery_date, barcode keys.

Revision ID: 0022_shipment_request_extended
Revises: 0021_company_api_keys
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = "0022_shipment_request_extended"
down_revision = "0021_company_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shipment_requests", sa.Column("order_id", sa.Integer(), nullable=True))
    op.add_column("shipment_requests", sa.Column("warehouse_name", sa.String(length=128), nullable=True))
    op.add_column("shipment_requests", sa.Column("delivery_date", sa.Date(), nullable=True))
    op.add_column("shipment_requests", sa.Column("supply_barcode_key", sa.String(length=512), nullable=True))
    op.add_column("shipment_requests", sa.Column("box_barcodes_key", sa.String(length=512), nullable=True))
    op.create_foreign_key(
        "fk_shipment_requests_order_id",
        "shipment_requests",
        "orders",
        ["order_id"],
        ["id"],
    )
    op.create_index("ix_shipment_requests_order_id", "shipment_requests", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_shipment_requests_order_id", table_name="shipment_requests")
    op.drop_constraint("fk_shipment_requests_order_id", "shipment_requests", type_="foreignkey")
    op.drop_column("shipment_requests", "box_barcodes_key")
    op.drop_column("shipment_requests", "supply_barcode_key")
    op.drop_column("shipment_requests", "delivery_date")
    op.drop_column("shipment_requests", "warehouse_name")
    op.drop_column("shipment_requests", "order_id")
