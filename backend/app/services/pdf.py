"""PDF generation service."""
from dataclasses import dataclass
import html

from weasyprint import HTML

from app.core.logging import logger


@dataclass
class LabelData:
    """Label data for 58x40 mm."""

    title: str
    article: str
    supplier: str
    barcode_value: str


@dataclass
class ContractData:
    """Contract data for PDF generation."""

    company_name: str
    inn: str
    director: str | None
    bank_bik: str | None
    bank_account: str | None


def render_label_pdf(label: LabelData) -> bytes:
    """Render label PDF for thermal printer."""
    try:
        title = html.escape(label.title or "")
        article = html.escape(label.article or "")
        supplier = html.escape(label.supplier or "")
        barcode_value = html.escape(label.barcode_value or "")
        html_content = f"""
        <html>
          <body style="width:58mm;height:40mm;margin:0;padding:4mm;font-family:Arial;">
            <div style="font-size:10pt;font-weight:bold;">{title}</div>
            <div style="font-size:8pt;">Артикул: {article}</div>
            <div style="font-size:8pt;">Поставщик: {supplier}</div>
            <div style="font-size:10pt;margin-top:6mm;">ШК: {barcode_value}</div>
          </body>
        </html>
        """
        return HTML(string=html_content).write_pdf()
    except Exception as exc:
        logger.exception("label_pdf_generation_failed", error=str(exc))
        raise


def render_contract_pdf(contract: ContractData) -> bytes:
    """Render a simple contract PDF."""
    try:
        company_name = html.escape(contract.company_name or "")
        inn = html.escape(contract.inn or "")
        director = html.escape(contract.director or "-")
        bank_bik = html.escape(contract.bank_bik or "-")
        bank_account = html.escape(contract.bank_account or "-")
        html_content = f"""
        <html>
          <body style="font-family:Arial; font-size:12pt;">
            <h2>Договор</h2>
            <p>Компания: {company_name}</p>
            <p>ИНН: {inn}</p>
            <p>Подписант: {director}</p>
            <h3>Реквизиты</h3>
            <p>БИК: {bank_bik}</p>
            <p>Расчетный счет: {bank_account}</p>
          </body>
        </html>
        """
        return HTML(string=html_content).write_pdf()
    except Exception as exc:
        logger.exception("contract_pdf_generation_failed", error=str(exc))
        raise
