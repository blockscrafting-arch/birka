"""PDF generation service."""
import base64
from dataclasses import dataclass
from io import BytesIO
import html

import barcode
from barcode.writer import ImageWriter
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
    kpp: str | None = None
    ogrn: str | None = None
    legal_address: str | None = None
    bank_name: str | None = None
    bank_corr_account: str | None = None


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
      <tr><td>ИНН / КПП</td><td>{{inn}} / {{kpp}}</td></tr>
      <tr><td>ОГРН</td><td>{{ogrn}}</td></tr>
      <tr><td>Юридический адрес</td><td>{{legal_address}}</td></tr>
      <tr><td>Подписант</td><td>{{director}}</td></tr>
      <tr><td>Банк</td><td>{{bank_name}}</td></tr>
      <tr><td>БИК</td><td>{{bank_bik}}</td></tr>
      <tr><td>Корр. счёт</td><td>{{bank_corr_account}}</td></tr>
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


def _render_barcode_base64(barcode_value: str, module_width: float = 0.35, module_height: float = 12) -> str:
    """Generate Code128 barcode as base64 PNG for embedding in HTML (58x40 label)."""
    if not barcode_value or not barcode_value.strip():
        return ""
    code = barcode_value.strip()
    try:
        code128 = barcode.get("code128", code, writer=ImageWriter())
        buf = BytesIO()
        opts = {"module_width": module_width, "module_height": module_height}
        try:
            code128.write(buf, options=opts)
        except TypeError:
            code128.write(buf)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as exc:
        logger.warning("barcode_png_failed", code=code, error=str(exc))
        return ""


def render_label_pdf(label: LabelData) -> bytes:
    """
    Render label PDF for TSC thermal printer 58x40 mm.
    Layout: title (name + size), Артикул, Поставщик, large barcode, number below (full sheet).
    """
    try:
        title = html.escape(label.title or "")
        article = html.escape(label.article or "")
        supplier = html.escape(label.supplier or "")
        barcode_value = html.escape(label.barcode_value or "")
        barcode_b64 = _render_barcode_base64(label.barcode_value or "")
        barcode_img = ""
        if barcode_b64:
            barcode_img = (
                f'<img src="data:image/png;base64,{barcode_b64}" alt="" '
                'style="display:block;margin:0 auto;max-width:54mm;height:auto;min-height:14mm;" />'
            )
        html_content = f"""
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8" />
            <style>
              @page {{ size: 58mm 40mm; margin: 0; }}
              html, body {{ margin: 0; padding: 0; width: 58mm; height: 40mm; font-family: Arial, sans-serif; overflow: hidden; box-sizing: border-box; }}
              .label {{ padding: 2mm; width: 56mm; min-height: 38mm; box-sizing: border-box; }}
              .label-title {{ font-weight: bold; font-size: 10pt; line-height: 1.2; margin-bottom: 1.5mm; word-break: break-word; }}
              .label-meta {{ font-size: 8pt; line-height: 1.35; margin-bottom: 1mm; }}
              .label-barcode {{ text-align: center; margin: 2mm 0; min-height: 14mm; display: flex; align-items: center; justify-content: center; }}
              .label-barcode img {{ max-width: 54mm; height: auto; }}
              .label-footer {{ font-size: 9pt; text-align: center; margin-top: 1mm; letter-spacing: 0.5px; }}
            </style>
          </head>
          <body>
            <div class="label">
              <div class="label-title">{title}</div>
              <div class="label-meta">Артикул {article}</div>
              <div class="label-meta">Поставщик {supplier}</div>
              <div class="label-barcode">{barcode_img}</div>
              <div class="label-footer">{barcode_value}</div>
            </div>
          </body>
        </html>
        """
        return HTML(string=html_content).write_pdf()
    except Exception as exc:
        logger.exception("label_pdf_generation_failed", error=str(exc))
        raise


def generate_price_list_pdf(services: list) -> bytes:
    """Generate PDF with price list (categories and services table)."""
    try:
        rows_html = []
        for s in services:
            cat = html.escape(str(getattr(s, "category", "")))
            name = html.escape(str(getattr(s, "name", "")))
            price = html.escape(str(getattr(s, "price", "")))
            unit = html.escape(str(getattr(s, "unit", "шт")))
            rows_html.append(f"<tr><td>{cat}</td><td>{name}</td><td>{price}</td><td>{unit}</td></tr>")
        table_body = "\n".join(rows_html)
        html_content = f"""
        <!doctype html>
        <html lang="ru">
          <head>
            <meta charset="utf-8" />
            <style>
              body {{ font-family: DejaVu Sans, Arial, sans-serif; font-size: 11pt; margin: 16px; }}
              h1 {{ text-align: center; font-size: 16pt; margin-bottom: 16px; }}
              table {{ width: 100%; border-collapse: collapse; }}
              th, td {{ padding: 6px 8px; border: 1px solid #ddd; text-align: left; }}
              th {{ background: #f5f5f5; font-weight: bold; }}
            </style>
          </head>
          <body>
            <h1>Прайс-лист Бирка</h1>
            <table>
              <thead>
                <tr><th>Категория</th><th>Услуга</th><th>Цена (₽)</th><th>Ед.</th></tr>
              </thead>
              <tbody>
                {table_body}
              </tbody>
            </table>
          </body>
        </html>
        """
        return HTML(string=html_content).write_pdf()
    except Exception as exc:
        logger.exception("price_list_pdf_failed", error=str(exc))
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
            "kpp": contract.kpp or "-",
            "ogrn": contract.ogrn or "-",
            "legal_address": contract.legal_address or "-",
            "bank_name": contract.bank_name or "-",
            "bank_corr_account": contract.bank_corr_account or "-",
        }
        html_content = _apply_contract_template(template_html or DEFAULT_CONTRACT_TEMPLATE, context)
        return HTML(string=html_content).write_pdf()
    except Exception as exc:
        logger.exception("contract_pdf_generation_failed", error=str(exc))
        raise
