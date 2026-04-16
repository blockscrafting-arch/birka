"""Products tests."""
import io

import pandas as pd

from app.services.excel import EXPORT_COLUMNS, export_products
from app.db.models.product import Product


async def test_create_product(client, auth_headers):
    company = await client.post("/api/v1/companies", json={"inn": "5556667770"}, headers=auth_headers)
    company_id = company.json()["id"]

    payload = {"company_id": company_id, "name": "Шлем"}
    response = await client.post("/api/v1/products", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Шлем"
    assert "created_at" in data
    assert isinstance(data["created_at"], str) and len(data["created_at"]) > 0


def test_export_columns_no_company_name():
    """Export columns must not include 'Название компании'."""
    assert "Название компании" not in EXPORT_COLUMNS


def test_export_columns_has_stock():
    """Export columns must include 'Остаток'."""
    assert "Остаток" in EXPORT_COLUMNS


def test_export_products_includes_stock():
    """Exported Excel includes Остаток column with values."""
    product = Product(
        id=1,
        company_id=1,
        name="Товар",
        brand=None,
        size=None,
        color=None,
        barcode=None,
        wb_article=None,
        wb_url=None,
        packing_instructions=None,
        supplier_name=None,
        stock_quantity=10,
        defect_quantity=0,
    )
    buf = export_products([product])
    buf.seek(0)
    df = pd.read_excel(buf)
    assert "Остаток" in df.columns
    assert list(df["Остаток"]) == [10]