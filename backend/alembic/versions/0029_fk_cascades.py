"""Add SET NULL cascades to FK constraints for safe order deletion.

Revision ID: 0029_fk_cascades
Revises: 0028_add_indexes
Create Date: 2026-04-09

"""
from alembic import op

revision = "0029_fk_cascades"
down_revision = "0028_add_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # shipment_request.order_id (named in 0022)
    op.drop_constraint("fk_shipment_requests_order_id", "shipment_requests", type_="foreignkey")
    op.create_foreign_key(
        "fk_shipment_requests_order_id",
        "shipment_requests",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # shipment_request.fbo_supply_id (named in 0023)
    op.drop_constraint("fk_shipment_requests_fbo_supply_id", "shipment_requests", type_="foreignkey")
    op.create_foreign_key(
        "fk_shipment_requests_fbo_supply_id",
        "shipment_requests",
        "fbo_supplies",
        ["fbo_supply_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # fbo_supply.order_id (auto-generated name from 0018, no explicit constraint name)
    op.drop_constraint("fbo_supplies_order_id_fkey", "fbo_supplies", type_="foreignkey")
    op.create_foreign_key(
        "fbo_supplies_order_id_fkey",
        "fbo_supplies",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fbo_supplies_order_id_fkey", "fbo_supplies", type_="foreignkey")
    op.create_foreign_key(
        "fbo_supplies_order_id_fkey", "fbo_supplies", "orders", ["order_id"], ["id"]
    )

    op.drop_constraint("fk_shipment_requests_fbo_supply_id", "shipment_requests", type_="foreignkey")
    op.create_foreign_key(
        "fk_shipment_requests_fbo_supply_id",
        "shipment_requests",
        "fbo_supplies",
        ["fbo_supply_id"],
        ["id"],
    )

    op.drop_constraint("fk_shipment_requests_order_id", "shipment_requests", type_="foreignkey")
    op.create_foreign_key(
        "fk_shipment_requests_order_id", "shipment_requests", "orders", ["order_id"], ["id"]
    )
