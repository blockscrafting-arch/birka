"""Import services (pricing) from built-in default data or from Excel/CSV file.

Usage:
  python -m scripts.import_services                    # load default прайс
  python -m scripts.import_services path/to/file.xlsx # load from Excel
  python -m scripts.import_services path/to/file.csv   # load from CSV

Run from backend directory: cd backend && python -m scripts.import_services
"""
from __future__ import annotations

import asyncio
import csv
import sys
from decimal import Decimal
from pathlib import Path

# Add backend to path so app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db.models.service import Service  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402

# Default прайс: Услуги, Первичная обработка, Обработка товара, Хранение, Пакеты и материалы, Отгрузка, Логистика
DEFAULT_SERVICES = [
    # 1. Услуги
    ("Услуги", "Забор товара с ТЯК/ЮВ/Садовод", "3500", "заказ", "зависит от объема, грузчики и въезд оплачивается отдельно", 1),
    ("Услуги", "Предоставление видеозаписи приема/отгрузки/упаковки заказа", "250", "заказ", "прописывается в ТЗ", 2),
    ("Услуги", "Доп. услуги менеджера (закрывающие документы в формате клиента)", "500", "услуга", "прописывается в ТЗ", 3),
    ("Услуги", "Создание поставки в кабинете Маркетплейса", "1000", "поставка", None, 4),
    ("Услуги", "Фотоотчет по товару", "50", "шт", None, 5),
    # 2. Первичная обработка
    ("Первичная обработка", "Приемка товара", "6", "шт", None, 10),
    ("Первичная обработка", "Сортировка товара (более 3-х артикулов в поставке)", "3.5", "шт", None, 11),
    ("Первичная обработка", "Разгрузка короб до 25 кг", "60", "короб", None, 12),
    ("Первичная обработка", "Разгрузка короб более 25 кг", "90", "короб", None, 13),
    ("Первичная обработка", "Разгрузка мешок", "175", "мешок", None, 14),
    ("Первичная обработка", "Снятие обрешетки с паллета", "450", "паллет", None, 15),
    ("Первичная обработка", "Снятие обрешетки с короба", "90", "короб", None, 16),
    ("Первичная обработка", "Разгрузка паллет", "240", "паллет", None, 17),
    # 3. Обработка товара
    ("Обработка товара", "Проверка соответствия образцу 1SKU", "290", "шт", None, 20),
    ("Обработка товара", "Проверка на брак S (товар до футболки/мини юбки)", "12", "шт", None, 21),
    ("Обработка товара", "Проверка на брак M (товар до штанов/пиджаков)", "18", "шт", None, 22),
    ("Обработка товара", "Проверка на брак L (верхняя одежда и обувь, сумки, рюкзаки)", "23", "шт", None, 23),
    ("Обработка товара", "Проверка на брак XL (пуховики/шубы/постельное белье)", "29", "шт", None, 24),
    ("Обработка товара", "Устранение мелкого брака (нитки, пятнышки и тд)", "12", "шт", None, 25),
    ("Обработка товара", "Проверка на брак техника (включить, вставить батарейки)", "12", "шт", None, 26),
    ("Обработка товара", "Внешний осмотр на брак заводской упаковки", "6", "шт", None, 27),
    ("Обработка товара", "Мелкие задачи (булавка, прорезать отверстие, застегнуть пуговицы, шнуровка)", "4", "шт", None, 28),
    ("Обработка товара", "Шнуровка обуви", "12", "шт", None, 29),
    ("Обработка товара", "Отпаривание S (до рубашки/штанов)", "60", "шт", None, 30),
    ("Обработка товара", "Отпаривание M (куртки/комбинизоны)", "70", "шт", None, 31),
    ("Обработка товара", "Навесить бирку (нейлон патрон/веревка/бирка входит в стоимость)", "7", "шт", None, 32),
    ("Обработка товара", "Вложение вкладыша (1-2 единицы)", "5", "шт", None, 33),
    ("Обработка товара", "Вложение вкладыша (от 2 до 5 единиц)", "8", "шт", None, 34),
    ("Обработка товара", "Вложение вкладыша (от 6 и более)", "14", "шт", None, 35),
    ("Обработка товара", "Сборка комплектов (1-2 единицы)", "6", "комплект", None, 36),
    ("Обработка товара", "Сборка комплектов (3-5 единиц)", "9", "комплект", None, 37),
    ("Обработка товара", "Сборка комплектов (от 6 и более единиц)", "15", "комплект", None, 38),
    ("Обработка товара", "Печать А4 (инструкции, вкладыши) 1 страница", "6", "стр", None, 39),
    ("Обработка товара", "Укрепление индивидуального короба", "6", "короб", None, 40),
    ("Обработка товара", "Маркировка товара", "4.5", "шт", None, 41),
    ("Обработка товара", "Двойная маркировка товара", "9", "шт", None, 42),
    ("Обработка товара", "Нанесение честного знака", "5.5", "шт", None, 43),
    ("Обработка товара", "Двойное нанесение честного знака", "10", "шт", None, 44),
    ("Обработка товара", "Снятие замеров", "290", "шт", None, 45),
    ("Обработка товара", "Упаковка товара в зип пакет", "6", "шт", None, 46),
    ("Обработка товара", "Упаковка товара в пузырчатую пленку S (до 30 см)", "15", "шт", None, 47),
    ("Обработка товара", "Упаковка товара в пузырчатую пленку M (до 60 см)", "25", "шт", None, 48),
    ("Обработка товара", "Упаковка товара в пузырчатую пленку L (до 100 см)", "35", "шт", None, 49),
    ("Обработка товара", "Упаковка товара в БОПП пакет", "6", "шт", None, 50),
    ("Обработка товара", "Упаковка товара в индивидуальный короб", "9", "шт", None, 51),
    ("Обработка товара", "Распределение маркированного товара по коробам", "3.5", "шт", None, 52),
    ("Обработка товара", "Приклеить шк коробов", "0", "шт", None, 53),
    ("Обработка товара", "Приклеить шк поставки", "0", "шт", None, 54),
    ("Обработка товара", "Закрепить коробку скотчем", "0", "короб", None, 55),
    # 4. Хранение (первая неделя бесплатно)
    ("Хранение", "1 короб/день", "7.5", "день", "первая неделя бесплатно; крупные клиенты индивидуально", 60),
    ("Хранение", "1 паллет/день", "75", "день", "первая неделя бесплатно; крупные клиенты индивидуально", 61),
    # 5. Пакеты и материалы — выборочно (основные)
    ("Пакеты и материалы", "Zip slider 14х17", "6", "шт", None, 70),
    ("Пакеты и материалы", "Короб 60*40*40", "100", "шт", None, 71),
    ("Пакеты и материалы", "Паллета 120*80", "300", "шт", None, 72),
    ("Пакеты и материалы", "ВПП пакет 10х15", "7", "шт", None, 73),
    ("Пакеты и материалы", "Курьер пакет 10х15", "3", "шт", None, 74),
    # 6. Отгрузка товара
    ("Отгрузка товара", "Формирование короба", "50", "короб", None, 80),
    ("Отгрузка товара", "Формирование паллета", "400", "паллет", None, 81),
    # 7. Логистика
    ("Логистика", "Коледино (короб)", "450", "короб", None, 90),
    ("Логистика", "Коледино (паллет)", "3000", "паллет", None, 91),
    ("Логистика", "Электросталь (короб)", "600", "короб", None, 92),
    ("Логистика", "Электросталь (паллет)", "4000", "паллет", None, 93),
    ("Логистика", "Тула Алексин (короб)", "450", "короб", None, 94),
    ("Логистика", "Тула Алексин (паллет)", "4500", "паллет", None, 95),
]


def _parse_price_cell(s: str) -> Decimal | None:
    """Extract numeric price from cell like '250,00 ₽', 'от 3500 ₽', '1 000,00 ₽'."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip().replace("\u00a0", " ").replace("₽", "").replace("от", "").strip()
    s = s.replace(",", ".")
    # Сначала пробуем как одно число (убираем пробелы между цифрами — разделитель тысяч)
    single = "".join(s.split())
    if single:
        try:
            return Decimal(single)
        except Exception:
            pass
    parts = s.split()
    for part in parts:
        part = part.strip(" \t()")
        if not part:
            continue
        try:
            return Decimal(part)
        except Exception:
            continue
    return None


def _parse_csv(path: Path) -> list[dict]:
    """Parse CSV with columns: category, name, price, unit, comment (semicolon or comma with headers)."""
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        if not reader.fieldnames:
            return rows
        for row in reader:
            cat = (row.get("Категория") or row.get("category") or "").strip()
            name = (row.get("Название") or row.get("name") or "").strip()
            if not cat or not name:
                continue
            price_str = (row.get("Цена") or row.get("price") or "0").replace(",", ".")
            try:
                price = Decimal(price_str)
            except Exception:
                price = Decimal("0")
            unit = (row.get("Ед.") or row.get("unit") or "шт").strip() or "шт"
            comment = (row.get("Комментарий") or row.get("comment") or "").strip() or None
            rows.append({"category": cat, "name": name, "price": price, "unit": unit, "comment": comment})
    if rows:
        return rows
    return _parse_csv_birka_format(path)


def _parse_csv_birka_format(path: Path) -> list[dict]:
    """Parse CSV in 'Прайс (копия)' format: comma delimiter, category rows (N. Name), service rows (• Name, price)."""
    import re

    result = []
    current_category = ""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=",", quotechar='"')
        for row in reader:
            if len(row) < 2:
                continue
            cell1 = (row[1] if len(row) > 1 else "").strip()
            cell2 = (row[2] if len(row) > 2 else "").strip()
            cell3 = (row[3] if len(row) > 3 else "").strip()
            if not cell1:
                continue
            if re.match(r"^\d+\.\s+\D", cell1) and not re.match(r"^\d+\.\d", cell1):
                if "Стоимость" in cell1 or "Комментарий" in cell1:
                    continue
                current_category = re.sub(r"^\d+\.\s*", "", cell1).strip()
                continue
            if re.match(r"^\d+\.\d", cell1):
                if "Пакеты" in current_category or "Zip" in cell1 or "БОПП" in cell1 or "ВПП" in cell1:
                    current_category = "Пакеты и материалы"
                continue
            price_val = _parse_price_cell(cell2)
            if price_val is None and len(row) > 3:
                price_val = _parse_price_cell(cell3)
            if price_val is not None and current_category:
                name = cell1.lstrip("•\t").strip()
                if len(name) < 2:
                    continue
                result.append({
                    "category": current_category,
                    "name": name[:256],
                    "price": price_val,
                    "unit": "шт",
                    "comment": cell3[:500] if cell3 and cell3 != cell2 else None,
                })
    return result


def _parse_excel(path: Path) -> list[dict]:
    """Parse Excel using app's parser."""
    from app.services.excel import parse_services_excel  # noqa: E402

    with open(path, "rb") as f:
        data = f.read()
    return parse_services_excel(data)


async def run_import(file_path: Path | None = None, replace: bool = True) -> int:
    """Import services. If file_path is None, use DEFAULT_SERVICES. If replace, clear existing first."""
    async with AsyncSessionLocal() as db:
        if replace:
            await db.execute(Service.__table__.delete())

        if file_path:
            suffix = file_path.suffix.lower()
            if suffix == ".csv":
                rows = _parse_csv(file_path)
            elif suffix in (".xlsx", ".xls"):
                rows = _parse_excel(file_path)
            else:
                raise ValueError(f"Unsupported format: {suffix}. Use .csv or .xlsx")
        else:
            rows = [
                {
                    "category": cat,
                    "name": name,
                    "price": Decimal(price),
                    "unit": unit,
                    "comment": comment,
                    "sort_order": sort_order,
                }
                for (cat, name, price, unit, comment, sort_order) in DEFAULT_SERVICES
            ]

        count = 0
        for i, r in enumerate(rows):
            sort_order = r.pop("sort_order", i) if "sort_order" in r else i
            if isinstance(r.get("price"), (int, float)):
                r["price"] = Decimal(str(r["price"]))
            service = Service(
                category=r["category"],
                name=r["name"],
                price=r["price"],
                unit=r.get("unit", "шт"),
                comment=r.get("comment"),
                is_active=True,
                sort_order=sort_order,
            )
            db.add(service)
            count += 1
        await db.commit()
        return count


def main() -> None:
    """CLI entry."""
    replace = True
    file_path = None
    args = [a for a in sys.argv[1:] if a != "--no-replace"]
    if "--no-replace" in sys.argv[1:]:
        replace = False
    if args and not args[0].startswith("-"):
        file_path = Path(args[0]).resolve()
        if not file_path.is_file():
            print(f"File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
    try:
        n = asyncio.run(run_import(file_path=file_path, replace=replace))
        print(f"Imported {n} services.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
