"""Add service_price_history table (audit).

Revision ID: 0011_service_price_history
Revises: 0010_services
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa


revision = "0011_service_price_history"
down_revision = "0010_services"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_price_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("old_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("new_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("changed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_service_price_history_service_id"), "service_price_history", ["service_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_service_price_history_service_id"), table_name="service_price_history")
    op.drop_table("service_price_history")
