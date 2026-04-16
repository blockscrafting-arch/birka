"""Add services table (pricing).

Revision ID: 0010_services
Revises: 0009_company_extended_fields
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa


revision = "0010_services"
down_revision = "0009_company_extended_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False, server_default="шт"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_services_category"), "services", ["category"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_services_category"), table_name="services")
    op.drop_table("services")
