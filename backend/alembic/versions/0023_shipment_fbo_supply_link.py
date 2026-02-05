"""Link shipment_requests to fbo_supplies; make fbo_supplies.order_id nullable.

Revision ID: 0023_shipment_fbo_supply_link
Revises: 0022_shipment_request_extended
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


revision = "0023_shipment_fbo_supply_link"
down_revision = "0022_shipment_request_extended"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shipment_requests",
        sa.Column("fbo_supply_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_shipment_requests_fbo_supply_id",
        "shipment_requests",
        "fbo_supplies",
        ["fbo_supply_id"],
        ["id"],
    )
    op.create_index("ix_shipment_requests_fbo_supply_id", "shipment_requests", ["fbo_supply_id"])

    op.alter_column(
        "fbo_supplies",
        "order_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "fbo_supplies",
        "order_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_index("ix_shipment_requests_fbo_supply_id", table_name="shipment_requests")
    op.drop_constraint("fk_shipment_requests_fbo_supply_id", "shipment_requests", type_="foreignkey")
    op.drop_column("shipment_requests", "fbo_supply_id")
