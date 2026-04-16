"""Add ai_settings table for AI provider and model selection.

Revision ID: 0017_ai_settings
Revises: 0016_chat_messages
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = "0017_ai_settings"
down_revision = "0016_chat_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="openai"),
        sa.Column("model", sa.String(length=128), nullable=False, server_default="gpt-4o-mini"),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO ai_settings (id, provider, model, temperature) VALUES (1, 'openai', 'gpt-4o-mini', 0.7)"
    )


def downgrade() -> None:
    op.drop_table("ai_settings")
