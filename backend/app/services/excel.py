"""Excel import/export helpers."""
from io import BytesIO

import pandas as pd

from app.core.logging import logger
from app.db.models.order import OrderItem
from app.db.models.packing_record import PackingRecord
from app.db.models.product import Product
from app.db.models.service import Service


EXPORT_COLUMNS = [
    "Название",
    "Название компании",
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

RECEIVING_COLUMNS = [
    "Баркод",
    "Название товара",
    "Дата приемки",
    "Кол-во план",
    "Кол-во факт",
    "Расхождения",
    "Комментарии",
]

SERVICES_COLUMNS = ["Категория", "Название", "Цена", "Ед.", "Комментарий", "Активна"]

FBO_COLUMNS = [
    "ID сотрудника",
    "Номер палета",
    "Номер короба",
    "Баркод",
    "Название товара",
    "Кол-во",
    "Склад",
    "Баркод короба",
]


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
            company_name = ""
            if product.company:
                company_name = product.company.name or ""
            rows.append(
                {
                    "Название": product.name,
                    "Название компании": company_name,
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


def export_receiving(order_items: list[OrderItem]) -> BytesIO:
    """Export receiving data (order items) to Excel."""
    try:
        rows = []
        for item in order_items:
            product = item.product
            order = item.order
            diff = (item.planned_qty or 0) - (item.received_qty or 0)
            rows.append(
                {
                    "Баркод": product.barcode if product else "",
                    "Название товара": product.name if product else "",
                    "Дата приемки": order.updated_at.strftime("%d.%m.%Y") if order else "",
                    "Кол-во план": item.planned_qty or 0,
                    "Кол-во факт": item.received_qty or 0,
                    "Расхождения": diff,
                    "Комментарии": item.adjustment_note or "",
                }
            )
        df = pd.DataFrame(rows, columns=RECEIVING_COLUMNS)
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        return buffer
    except Exception as exc:
        logger.exception("excel_export_receiving_failed", error=str(exc))
        raise


def export_fbo_shipping(packing_records: list[PackingRecord]) -> BytesIO:
    """Export FBO shipping (packing records) to Excel."""
    try:
        sorted_records = sorted(
            packing_records,
            key=lambda r: (
                r.pallet_number if r.pallet_number is not None else 0,
                r.box_number if r.box_number is not None else 0,
            ),
        )
        rows = []
        for rec in sorted_records:
            product = rec.product
            employee = rec.employee
            rows.append(
                {
                    "ID сотрудника": employee.employee_code if employee else "",
                    "Номер палета": rec.pallet_number or "",
                    "Номер короба": rec.box_number or "",
                    "Баркод": product.barcode if product else "",
                    "Название товара": product.name if product else "",
                    "Кол-во": rec.quantity or 0,
                    "Склад": rec.warehouse or "",
                    "Баркод короба": rec.box_barcode or "",
                }
            )
        df = pd.DataFrame(rows, columns=FBO_COLUMNS)
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        return buffer
    except Exception as exc:
        logger.exception("excel_export_fbo_failed", error=str(exc))
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


def export_services(services: list[Service]) -> BytesIO:
    """Export services (pricing) to Excel in-memory file."""
    try:
        rows = []
        for s in services:
            rows.append(
                {
                    "Категория": s.category,
                    "Название": s.name,
                    "Цена": float(s.price),
                    "Ед.": s.unit,
                    "Комментарий": s.comment or "",
                    "Активна": "Да" if s.is_active else "Нет",
                }
            )
        df = pd.DataFrame(rows, columns=SERVICES_COLUMNS)
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        return buffer
    except Exception as exc:
        logger.exception("excel_export_services_failed", error=str(exc))
        raise


def parse_services_excel(file_bytes: bytes) -> list[dict]:
    """Parse services from Excel bytes. Columns: Категория, Название, Цена, Ед., Комментарий."""
    try:
        df = pd.read_excel(BytesIO(file_bytes))
        required = {"Категория", "Название", "Цена"}
        missing = required.difference(set(df.columns))
        if missing:
            raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
        df = df.fillna("")
        services = []
        for _, row in df.iterrows():
            cat = str(row.get("Категория", "")).strip()
            name = str(row.get("Название", "")).strip()
            if not cat or not name:
                continue
            price_val = row.get("Цена", 0)
            try:
                price = float(price_val) if price_val != "" else 0.0
            except (TypeError, ValueError):
                price = 0.0
            unit = str(row.get("Ед.", "шт")).strip() or "шт"
            comment = str(row.get("Комментарий", "")).strip() or None
            services.append(
                {
                    "category": cat,
                    "name": name,
                    "price": price,
                    "unit": unit,
                    "comment": comment,
                }
            )
        return services
    except Exception as exc:
        logger.exception("excel_parse_services_failed", error=str(exc))
        raise
