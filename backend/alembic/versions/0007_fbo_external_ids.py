"""Add external_box_id to FBO supply boxes.

Revision ID: 0007_fbo_external_ids
Revises: 0006_fbo_supplies
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa


revision = "0007_fbo_external_ids"
down_revision = "0006_fbo_supplies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fbo_supply_boxes",
        sa.Column("external_box_id", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("fbo_supply_boxes", "external_box_id")
