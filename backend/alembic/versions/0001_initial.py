"""Initial schema.

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-29
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("telegram_username", sa.String(length=64)),
        sa.Column("first_name", sa.String(length=128)),
        sa.Column("last_name", sa.String(length=128)),
        sa.Column("role", sa.String(length=32)),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("inn", sa.String(length=16), nullable=False, unique=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("legal_form", sa.String(length=32)),
        sa.Column("director", sa.String(length=128)),
        sa.Column("bank_bik", sa.String(length=16)),
        sa.Column("bank_account", sa.String(length=32)),
        sa.Column("contract_data", sa.JSON()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_companies_inn", "companies", ["inn"])
    op.create_index("ix_companies_user_id", "companies", ["user_id"])

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id")),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("brand", sa.String(length=128)),
        sa.Column("size", sa.String(length=64)),
        sa.Column("color", sa.String(length=64)),
        sa.Column("barcode", sa.String(length=64), unique=True),
        sa.Column("wb_article", sa.String(length=64)),
        sa.Column("wb_url", sa.String(length=512)),
        sa.Column("packing_instructions", sa.Text()),
        sa.Column("stock_quantity", sa.Integer(), default=0),
        sa.Column("defect_quantity", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_products_company_id", "products", ["company_id"])
    op.create_index("ix_products_barcode", "products", ["barcode"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id")),
        sa.Column("order_number", sa.String(length=64), unique=True),
        sa.Column("status", sa.String(length=32)),
        sa.Column("destination", sa.String(length=64)),
        sa.Column("planned_qty", sa.Integer(), default=0),
        sa.Column("received_qty", sa.Integer(), default=0),
        sa.Column("packed_qty", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_orders_company_id", "orders", ["company_id"])
    op.create_index("ix_orders_order_number", "orders", ["order_number"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id")),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id")),
        sa.Column("planned_qty", sa.Integer(), default=0),
        sa.Column("received_qty", sa.Integer(), default=0),
        sa.Column("packed_qty", sa.Integer(), default=0),
        sa.Column("defect_qty", sa.Integer(), default=0),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_items_product_id", "order_items", ["product_id"])

    op.create_table(
        "order_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id")),
        sa.Column("s3_key", sa.String(length=512), nullable=False),
        sa.Column("photo_type", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_order_photos_order_id", "order_photos", ["order_id"])

    op.create_table(
        "warehouse_employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("employee_code", sa.String(length=32), unique=True),
        sa.Column("is_active", sa.Boolean(), default=True),
    )
    op.create_index("ix_warehouse_employees_employee_code", "warehouse_employees", ["employee_code"])

    op.create_table(
        "packing_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id")),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id")),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("warehouse_employees.id")),
        sa.Column("pallet_number", sa.Integer()),
        sa.Column("box_number", sa.Integer()),
        sa.Column("quantity", sa.Integer()),
        sa.Column("warehouse", sa.String(length=128)),
        sa.Column("box_barcode", sa.String(length=128)),
        sa.Column("materials_used", sa.Text()),
        sa.Column("time_spent_minutes", sa.Integer()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_packing_records_order_id", "packing_records", ["order_id"])
    op.create_index("ix_packing_records_product_id", "packing_records", ["product_id"])
    op.create_index("ix_packing_records_employee_id", "packing_records", ["employee_id"])

    op.create_table(
        "product_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id")),
        sa.Column("s3_key", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_product_photos_product_id", "product_photos", ["product_id"])


def downgrade() -> None:
    op.drop_table("product_photos")
    op.drop_table("packing_records")
    op.drop_table("warehouse_employees")
    op.drop_table("order_photos")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("products")
    op.drop_table("companies")
    op.drop_table("users")
