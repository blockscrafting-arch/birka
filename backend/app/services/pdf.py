"""PDF generation service."""
import base64
from dataclasses import dataclass
from io import BytesIO
import html

import barcode
from barcode.writer import SVGWriter
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
    contract_number: str
    contract_date: str
    service_description: str


DEFAULT_CONTRACT_TEMPLATE = """
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <style>
      body { font-family: DejaVu Sans, Arial, sans-serif; font-size: 12pt; line-height: 1.4; }
      h1, h2 { text-align: center; margin: 0 0 12px; }
      h1 { font-size: 16pt; }
      h2 { font-size: 13pt; }
      .section-title { font-weight: bold; margin-top: 16px; }
      .muted { color: #666; font-size: 10pt; }
      table { width: 100%; border-collapse: collapse; margin-top: 8px; }
      td { padding: 6px 4px; border-bottom: 1px solid #ddd; vertical-align: top; }
    </style>
  </head>
  <body>
    <h1>Договор оказания услуг № {{contract_number}} от {{contract_date}}</h1>
    <p>г. ____________</p>
    <p>
      {{company_name}}, именуемое в дальнейшем «Заказчик», в лице {{director}},
      действующего на основании устава, с одной стороны, и Исполнитель, с другой стороны,
      заключили настоящий договор о нижеследующем.
    </p>

    <div class="section-title">1. Предмет договора</div>
    <p>{{service_description}}</p>

    <div class="section-title">2. Права и обязанности сторон</div>
    <p>
      Исполнитель обязуется оказывать услуги надлежащего качества, а Заказчик — принимать
      и оплачивать оказанные услуги в порядке и сроки, предусмотренные настоящим договором.
    </p>

    <div class="section-title">3. Стоимость и порядок расчетов</div>
    <p>
      Стоимость услуг определяется дополнительными соглашениями и счетами Исполнителя.
      Оплата производится в течение 5 (пяти) рабочих дней с момента выставления счета.
    </p>

    <div class="section-title">4. Ответственность сторон</div>
    <p>
      Стороны несут ответственность за неисполнение или ненадлежащее исполнение обязательств
      в соответствии с законодательством Российской Федерации.
    </p>

    <div class="section-title">5. Заключительные положения</div>
    <p>
      Настоящий договор вступает в силу с даты его подписания и действует бессрочно до момента
      расторжения по соглашению сторон либо в иных случаях, предусмотренных законом.
    </p>

    <div class="section-title">6. Реквизиты Заказчика</div>
    <table>
      <tr><td>Наименование</td><td>{{company_name}}</td></tr>
      <tr><td>ИНН</td><td>{{inn}}</td></tr>
      <tr><td>Подписант</td><td>{{director}}</td></tr>
      <tr><td>БИК</td><td>{{bank_bik}}</td></tr>
      <tr><td>Расчетный счет</td><td>{{bank_account}}</td></tr>
    </table>

    <div class="section-title">Подписи сторон</div>
    <table>
      <tr>
        <td>Заказчик: ____________________ / {{director}} /</td>
        <td>Исполнитель: ____________________ / ____________ /</td>
      </tr>
    </table>
    <p class="muted">Шаблон можно редактировать в админке.</p>
  </body>
</html>
""".strip()


def _apply_contract_template(template_html: str, context: dict[str, str]) -> str:
    """Apply template placeholders with escaped values."""
    html_content = template_html
    for key, value in context.items():
        safe_value = html.escape(value or "-")
        html_content = html_content.replace(f"{{{{{key}}}}}", safe_value)
    return html_content


def _render_barcode_svg(barcode_value: str) -> str:
    """Generate EAN13 barcode as SVG string for embedding in HTML."""
    if not barcode_value or not barcode_value.strip():
        return ""
    code = barcode_value.strip()
    if len(code) == 13:
        code = code[:12]
    elif len(code) != 12:
        return ""
    try:
        ean = barcode.get("ean13", code, writer=SVGWriter())
        buf = BytesIO()
        ean.write(buf)
        return buf.getvalue().decode("utf-8")
    except Exception as exc:
        logger.warning("barcode_svg_failed", code=code, error=str(exc))
        return ""


def render_label_pdf(label: LabelData) -> bytes:
    """Render label PDF for thermal printer with graphical barcode."""
    try:
        title = html.escape(label.title or "")
        article = html.escape(label.article or "")
        supplier = html.escape(label.supplier or "")
        barcode_value = html.escape(label.barcode_value or "")
        barcode_svg = _render_barcode_svg(label.barcode_value or "")
        barcode_img = ""
        if barcode_svg:
            b64 = base64.b64encode(barcode_svg.encode("utf-8")).decode("ascii")
            barcode_img = f'<img src="data:image/svg+xml;base64,{b64}" alt="" style="max-width:100%;height:auto;" />'
        html_content = f"""
        <html>
          <body style="width:58mm;height:40mm;margin:0;padding:3mm;font-family:Arial;">
            <div style="font-size:9pt;font-weight:bold;line-height:1.2;">{title}</div>
            <table style="font-size:7pt;margin-top:2mm;border-collapse:collapse;">
              <tr><td>Артикул</td><td style="padding-left:4mm;">{article}</td></tr>
              <tr><td>Поставщик</td><td style="padding-left:4mm;">{supplier}</td></tr>
            </table>
            <div style="margin-top:3mm;text-align:center;">
              {barcode_img}
            </div>
            <div style="font-size:8pt;text-align:center;">{barcode_value}</div>
          </body>
        </html>
        """
        return HTML(string=html_content).write_pdf()
    except Exception as exc:
        logger.exception("label_pdf_generation_failed", error=str(exc))
        raise


def render_contract_pdf(contract: ContractData, template_html: str | None = None) -> bytes:
    """Render a contract PDF using HTML template."""
    try:
        context = {
            "company_name": contract.company_name or "-",
            "inn": contract.inn or "-",
            "director": contract.director or "-",
            "bank_bik": contract.bank_bik or "-",
            "bank_account": contract.bank_account or "-",
            "contract_number": contract.contract_number or "-",
            "contract_date": contract.contract_date or "-",
            "service_description": contract.service_description or "-",
        }
        html_content = _apply_contract_template(template_html or DEFAULT_CONTRACT_TEMPLATE, context)
        return HTML(string=html_content).write_pdf()
    except Exception as exc:
        logger.exception("contract_pdf_generation_failed", error=str(exc))
        raise
