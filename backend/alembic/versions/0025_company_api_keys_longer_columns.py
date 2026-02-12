"""Widen company_api_keys columns for encrypted WB/Ozon tokens.

Encrypted Fernet output can exceed 512 chars for long JWT API keys.
Revision ID: 0025_company_api_keys_longer
Revises: 0024_fbo_supply_box_external_id
"""
from alembic import op
import sqlalchemy as sa


revision = "0025_company_api_keys_longer"
down_revision = "0024_fbo_supply_box_external_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "company_api_keys",
        "wb_api_key",
        existing_type=sa.String(length=512),
        type_=sa.String(length=2048),
        existing_nullable=True,
    )
    op.alter_column(
        "company_api_keys",
        "ozon_client_id",
        existing_type=sa.String(length=128),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
    op.alter_column(
        "company_api_keys",
        "ozon_api_key",
        existing_type=sa.String(length=512),
        type_=sa.String(length=2048),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "company_api_keys",
        "wb_api_key",
        existing_type=sa.String(length=2048),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
    op.alter_column(
        "company_api_keys",
        "ozon_client_id",
        existing_type=sa.String(length=512),
        type_=sa.String(length=128),
        existing_nullable=True,
    )
    op.alter_column(
        "company_api_keys",
        "ozon_api_key",
        existing_type=sa.String(length=2048),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
