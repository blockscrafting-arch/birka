"""Add order_counters table.

Revision ID: 0003_order_counters
Revises: 0002_sessions
Create Date: 2026-01-29
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_order_counters"
down_revision = "0002_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_counters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("counter_date", sa.Date(), unique=True, nullable=False),
        sa.Column("value", sa.Integer(), default=0),
    )
    op.create_index("ix_order_counters_counter_date", "order_counters", ["counter_date"])


def downgrade() -> None:
    op.drop_table("order_counters")
