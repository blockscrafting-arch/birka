"""Add order_services table (order-service link with price snapshot).

Revision ID: 0012_order_services
Revises: 0011_service_price_history
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa


revision = "0012_order_services"
down_revision = "0011_service_price_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_services",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("price_at_order", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_services_order_id"), "order_services", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_services_service_id"), "order_services", ["service_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_order_services_service_id"), table_name="order_services")
    op.drop_index(op.f("ix_order_services_order_id"), table_name="order_services")
    op.drop_table("order_services")
