"""Add FBO supplies tables.

Revision ID: 0006_fbo_supplies
Revises: 0005_company_api_keys
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa


revision = "0006_fbo_supplies"
down_revision = "0005_company_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fbo_supplies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("marketplace", sa.String(length=16), nullable=False),
        sa.Column("external_supply_id", sa.String(length=128), nullable=True),
        sa.Column("warehouse_name", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_fbo_supplies_company_id", "fbo_supplies", ["company_id"])

    op.create_table(
        "fbo_supply_boxes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supply_id", sa.Integer(), sa.ForeignKey("fbo_supplies.id"), nullable=False),
        sa.Column("box_number", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.String(length=128), nullable=True),
        sa.Column("sticker_s3_key", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_fbo_supply_boxes_supply_id", "fbo_supply_boxes", ["supply_id"])

    op.create_table(
        "fbo_supply_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("box_id", sa.Integer(), sa.ForeignKey("fbo_supply_boxes.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_fbo_supply_items_box_id", "fbo_supply_items", ["box_id"])
    op.create_index("ix_fbo_supply_items_product_id", "fbo_supply_items", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_fbo_supply_items_product_id", table_name="fbo_supply_items")
    op.drop_index("ix_fbo_supply_items_box_id", table_name="fbo_supply_items")
    op.drop_table("fbo_supply_items")
    op.drop_index("ix_fbo_supply_boxes_supply_id", table_name="fbo_supply_boxes")
    op.drop_table("fbo_supply_boxes")
    op.drop_index("ix_fbo_supplies_company_id", table_name="fbo_supplies")
    op.drop_table("fbo_supplies")
