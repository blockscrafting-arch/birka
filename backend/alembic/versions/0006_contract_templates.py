"""Add contract templates table.

Revision ID: 0006_contract_templates
Revises: 0005_destinations
Create Date: 2026-02-01
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_contract_templates"
down_revision = "0005_destinations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contract_templates_is_default", "contract_templates", ["is_default"])

    default_template = """
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
    op.execute(
        sa.text(
            """
            INSERT INTO contract_templates (name, html_content, is_default, created_at, updated_at)
            VALUES (:name, :html_content, true, now(), now())
            """
        ).bindparams(name="Базовый договор", html_content=default_template)
    )


def downgrade() -> None:
    op.drop_index("ix_contract_templates_is_default", table_name="contract_templates")
    op.drop_table("contract_templates")
