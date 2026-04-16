"""Add performance indexes.

Revision ID: 0028_add_indexes
Revises: 0027_document_chunks_section
Create Date: 2026-04-09

"""
from alembic import op

revision = "0028_add_indexes"
down_revision = "0027_document_chunks_section"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_barcode_scan_log_barcode", "barcode_scan_log", ["barcode"])
    op.create_index(
        "ix_orders_company_status_created",
        "orders",
        ["company_id", "status", "created_at"],
    )
    op.create_index(
        "ix_order_items_order_product",
        "order_items",
        ["order_id", "product_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_order_items_order_product", table_name="order_items")
    op.drop_index("ix_orders_company_status_created", table_name="orders")
    op.drop_index("ix_barcode_scan_log_barcode", table_name="barcode_scan_log")
