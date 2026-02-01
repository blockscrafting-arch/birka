"""Excel import/export helpers."""
from io import BytesIO

import pandas as pd

from app.core.logging import logger
from app.db.models.product import Product


EXPORT_COLUMNS = [
    "Название",
    "Бренд",
    "Размер",
    "Цвет",
    "Баркод",
    "Артикул WB",
    "Ссылка WB",
    "ТЗ упаковка",
    "Поставщик",
]
REQUIRED_COLUMNS = {"Название", "Баркод", "Артикул WB", "Поставщик"}


def export_products_template() -> BytesIO:
    """Export empty Excel template with required columns."""
    buffer = BytesIO()
    pd.DataFrame(columns=EXPORT_COLUMNS).to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer


def export_products(products: list[Product]) -> BytesIO:
    """Export products to Excel in-memory file."""
    try:
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
                "Поставщик": product.supplier_name,
                }
            )
        df = pd.DataFrame(rows, columns=EXPORT_COLUMNS)
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        return buffer
    except Exception as exc:
        logger.exception("excel_export_failed", error=str(exc))
        raise


def parse_products_excel(file_bytes: bytes) -> list[dict]:
    """Parse products from Excel bytes."""
    try:
        df = pd.read_excel(BytesIO(file_bytes))
        missing = REQUIRED_COLUMNS.difference(set(df.columns))
        if missing:
            raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
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
                    "supplier_name": str(row.get("Поставщик", "")).strip() or None,
                }
            )
        return products
    except Exception as exc:
        logger.exception("excel_parse_failed", error=str(exc))
        raise
