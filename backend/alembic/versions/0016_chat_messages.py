"""Add chat_messages table for AI chat history.

Revision ID: 0016_chat_messages
Revises: 0015_contract_template_single_default
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa


revision = "0016_chat_messages"
down_revision = "0015_contract_template_single_default"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_chat_messages_company_id", "chat_messages", ["company_id"])
    op.create_index(
        "ix_chat_messages_user_company_created",
        "chat_messages",
        ["user_id", "company_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_user_company_created", table_name="chat_messages")
    op.drop_index("ix_chat_messages_company_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_user_id", table_name="chat_messages")
    op.drop_table("chat_messages")
