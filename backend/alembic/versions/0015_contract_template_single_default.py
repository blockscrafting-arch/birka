"""Ensure at most one contract template has is_default=true (partial unique index).

Revision ID: 0015_contract_template_single_default
Revises: 0014_contract_template_files
Create Date: 2026-02-04

"""
from alembic import op


revision = "0015_contract_template_single_default"
down_revision = "0014_contract_template_files"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    # Normalize: at most one is_default=true (keep the latest by updated_at, then id)
    op.execute("UPDATE contract_templates SET is_default = false")
    if dialect == "postgresql":
        op.execute(
            "UPDATE contract_templates SET is_default = true WHERE id = ("
            "SELECT id FROM contract_templates ORDER BY updated_at DESC, id DESC LIMIT 1"
            ")"
        )
    elif dialect == "sqlite":
        op.execute(
            "UPDATE contract_templates SET is_default = 1 WHERE id = ("
            "SELECT id FROM contract_templates ORDER BY updated_at DESC, id DESC LIMIT 1"
            ")"
        )

    if dialect == "postgresql":
        op.execute(
            "CREATE UNIQUE INDEX ix_contract_templates_single_default "
            "ON contract_templates (is_default) WHERE is_default = true"
        )
    elif dialect == "sqlite":
        op.execute(
            "CREATE UNIQUE INDEX ix_contract_templates_single_default "
            "ON contract_templates (is_default) WHERE is_default = 1"
        )


def downgrade() -> None:
    op.drop_index(
        "ix_contract_templates_single_default",
        table_name="contract_templates",
    )
