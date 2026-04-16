"""Add barcode_scan_log table for scanner journal.

Revision ID: 0026_barcode_scan_log
Revises: 0025_company_api_keys_longer
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa


revision = "0026_barcode_scan_log"
down_revision = "0025_company_api_keys_longer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "barcode_scan_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("barcode", sa.String(length=128), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("scanned_at", sa.DateTime(), nullable=False),
        sa.Column("valid", sa.Boolean(), nullable=False),
        sa.Column("result_type", sa.String(length=16), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("fbo_supply_box_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fbo_supply_box_id"], ["fbo_supply_boxes.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_barcode_scan_log_user_id", "barcode_scan_log", ["user_id"])
    op.create_index("ix_barcode_scan_log_company_id", "barcode_scan_log", ["company_id"])
    op.create_index("ix_barcode_scan_log_scanned_at", "barcode_scan_log", ["scanned_at"])
    op.create_index("ix_barcode_scan_log_order_id", "barcode_scan_log", ["order_id"])
    op.create_index("ix_barcode_scan_log_product_id", "barcode_scan_log", ["product_id"])
    op.create_index("ix_barcode_scan_log_fbo_supply_box_id", "barcode_scan_log", ["fbo_supply_box_id"])


def downgrade() -> None:
    op.drop_index("ix_barcode_scan_log_fbo_supply_box_id", "barcode_scan_log")
    op.drop_index("ix_barcode_scan_log_product_id", "barcode_scan_log")
    op.drop_index("ix_barcode_scan_log_order_id", "barcode_scan_log")
    op.drop_index("ix_barcode_scan_log_scanned_at", "barcode_scan_log")
    op.drop_index("ix_barcode_scan_log_company_id", "barcode_scan_log")
    op.drop_index("ix_barcode_scan_log_user_id", "barcode_scan_log")
    op.drop_table("barcode_scan_log")
