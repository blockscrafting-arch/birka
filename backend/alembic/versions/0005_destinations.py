"""Add destinations table (address/shipment lookup).

Revision ID: 0005_destinations
Revises: 0004_shipping_and_adjustments
Create Date: 2026-02-01

"""
from alembic import op
import sqlalchemy as sa


revision = "0005_destinations"
down_revision = "0004_shipping_and_adjustments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "destinations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_destinations_is_active", "destinations", ["is_active"])

    op.execute(
        sa.text(
            """
            INSERT INTO destinations (name, is_active)
            VALUES
                ('Котовск', true),
                ('Невинномысск', true),
                ('Тула', true),
                ('Воронеж (самовывоз)', true)
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_destinations_is_active", table_name="destinations")
    op.drop_table("destinations")
