"""Add order completed_at.

Revision ID: 0007_order_completed_at
Revises: 0006_contract_templates
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa


revision = "0007_order_completed_at"
down_revision = "0006_contract_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("completed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "completed_at")
