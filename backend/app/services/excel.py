"""Excel import/export helpers."""
from io import BytesIO

import pandas as pd

from app.db.models.product import Product


def export_products(products: list[Product]) -> BytesIO:
    """Export products to Excel in-memory file."""
    rows = []
    for product in products:
        rows.append(
            {
                "Название": product.name,
                "Бренд": product.brand,
                "Размер": product.size,
                "Цвет": product.color,
                "Баркод": product.barcode,
                "Артикул WB": product.wb_article,
                "Ссылка WB": product.wb_url,
                "ТЗ упаковка": product.packing_instructions,
            }
        )
    df = pd.DataFrame(rows)
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer


def parse_products_excel(file_bytes: bytes) -> list[dict]:
    """Parse products from Excel bytes."""
    df = pd.read_excel(BytesIO(file_bytes))
    df = df.fillna("")
    products = []
    for _, row in df.iterrows():
        products.append(
            {
                "name": str(row.get("Название", "")).strip(),
                "brand": str(row.get("Бренд", "")).strip() or None,
                "size": str(row.get("Размер", "")).strip() or None,
                "color": str(row.get("Цвет", "")).strip() or None,
                "barcode": str(row.get("Баркод", "")).strip() or None,
                "wb_article": str(row.get("Артикул WB", "")).strip() or None,
                "wb_url": str(row.get("Ссылка WB", "")).strip() or None,
                "packing_instructions": str(row.get("ТЗ упаковка", "")).strip() or None,
            }
        )
    return products
