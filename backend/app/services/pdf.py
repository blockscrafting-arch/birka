"""PDF generation service."""
from dataclasses import dataclass

from weasyprint import HTML


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
    html = f"""
    <html>
      <body style="width:58mm;height:40mm;margin:0;padding:4mm;font-family:Arial;">
        <div style="font-size:10pt;font-weight:bold;">{label.title}</div>
        <div style="font-size:8pt;">Артикул: {label.article}</div>
        <div style="font-size:8pt;">Поставщик: {label.supplier}</div>
        <div style="font-size:10pt;margin-top:6mm;">ШК: {label.barcode_value}</div>
      </body>
    </html>
    """
    return HTML(string=html).write_pdf()


def render_contract_pdf(contract: ContractData) -> bytes:
    """Render a simple contract PDF."""
    html = f"""
    <html>
      <body style="font-family:Arial; font-size:12pt;">
        <h2>Договор</h2>
        <p>Компания: {contract.company_name}</p>
        <p>ИНН: {contract.inn}</p>
        <p>Подписант: {contract.director or "-"}</p>
        <h3>Реквизиты</h3>
        <p>БИК: {contract.bank_bik or "-"}</p>
        <p>Расчетный счет: {contract.bank_account or "-"}</p>
      </body>
    </html>
    """
    return HTML(string=html).write_pdf()
