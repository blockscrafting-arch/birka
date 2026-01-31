"""Add sessions table.

Revision ID: 0002_sessions
Revises: 0001_initial
Create Date: 2026-01-29
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_sessions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("token", sa.String(length=64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("expires_at", sa.DateTime()),
    )
    op.create_index("ix_sessions_token", "sessions", ["token"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])


def downgrade() -> None:
    op.drop_table("sessions")
