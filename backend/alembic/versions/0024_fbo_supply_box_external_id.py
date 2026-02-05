"""Add external_box_id to fbo_supply_boxes.

Revision ID: 0024_fbo_supply_box_external_id
Revises: 0023_shipment_fbo_supply_link
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = "0024_fbo_supply_box_external_id"
down_revision = "0023_shipment_fbo_supply_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fbo_supply_boxes",
        sa.Column("external_box_id", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("fbo_supply_boxes", "external_box_id")
