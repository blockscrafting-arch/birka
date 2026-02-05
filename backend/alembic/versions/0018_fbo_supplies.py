"""Add FBO supplies tables for WB/Ozon integration.

Revision ID: 0018_fbo_supplies
Revises: 0017_ai_settings
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = "0018_fbo_supplies"
down_revision = "0017_ai_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fbo_supplies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("marketplace", sa.String(length=32), nullable=False),
        sa.Column("external_supply_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("warehouse_name", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fbo_supplies_order_id", "fbo_supplies", ["order_id"])
    op.create_index("ix_fbo_supplies_company_id", "fbo_supplies", ["company_id"])

    op.create_table(
        "fbo_supply_boxes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("supply_id", sa.Integer(), nullable=False),
        sa.Column("box_number", sa.Integer(), nullable=False),
        sa.Column("external_barcode", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["supply_id"], ["fbo_supplies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fbo_supply_boxes_supply_id", "fbo_supply_boxes", ["supply_id"])

    op.create_table(
        "fbo_supply_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("box_id", sa.Integer(), nullable=False),
        sa.Column("packing_record_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["box_id"], ["fbo_supply_boxes.id"]),
        sa.ForeignKeyConstraint(["packing_record_id"], ["packing_records.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fbo_supply_items_box_id", "fbo_supply_items", ["box_id"])


def downgrade() -> None:
    op.drop_index("ix_fbo_supply_items_box_id", table_name="fbo_supply_items")
    op.drop_table("fbo_supply_items")
    op.drop_index("ix_fbo_supply_boxes_supply_id", table_name="fbo_supply_boxes")
    op.drop_table("fbo_supply_boxes")
    op.drop_index("ix_fbo_supplies_company_id", table_name="fbo_supplies")
    op.drop_index("ix_fbo_supplies_order_id", table_name="fbo_supplies")
    op.drop_table("fbo_supplies")
