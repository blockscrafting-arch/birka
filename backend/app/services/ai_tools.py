"""AI assistant tools: function definitions and execution for OpenAI function calling."""
import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models.company import Company
from app.db.models.destination import Destination
from app.db.models.order import Order, OrderItem
from app.db.models.order_service import OrderService
from app.db.models.product import Product
from app.db.models.service import Service
from app.db.models.shipment_request import ShipmentRequest
from app.db.models.user import User

# Limits for tool responses to avoid token overflow and slow replies
MAX_ORDERS = 50
MAX_PRODUCTS = 50
MAX_SERVICES = 100
MAX_DESTINATIONS = 50
MAX_SHIPMENT_REQUESTS = 50
MAX_DEFECT_ITEMS = 20

# Canonical order statuses in DB
ORDER_STATUSES = frozenset({"На приемке", "Принято", "Упаковка", "Готово к отгрузке", "Завершено"})
# Synonyms / user phrases -> canonical status
ORDER_STATUS_SYNONYMS = {
    "на приемке": "На приемке",
    "приемка": "На приемке",
    "принято": "Принято",
    "принят": "Принято",
    "упаковка": "Упаковка",
    "упаковывается": "Упаковка",
    "готово к отгрузке": "Готово к отгрузке",
    "готов к отгрузке": "Готово к отгрузке",
    "отгрузка": "Готово к отгрузке",
    "завершено": "Завершено",
    "завершен": "Завершено",
    "отгружено": "Завершено",
    "отгружены": "Завершено",
    "выполнено": "Завершено",
    "готово": "Завершено",
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_orders",
            "description": "Получить список заявок пользователя. Можно фильтровать по статусу: На приемке, Принято, Упаковка, Готово к отгрузке, Завершено.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Фильтр по статусу заявки или синониму (отгружено, завершено, упаковка и т.д.)."},
                    "statuses": {"type": "array", "items": {"type": "string"}, "description": "Несколько статусов для фильтра (опционально)."},
                    "limit": {"type": "integer", "description": "Макс. число заявок в ответе (по умолчанию 20)."},
                    "offset": {"type": "integer", "description": "Смещение для пагинации (по умолчанию 0)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_details",
            "description": "Детали конкретной заявки по номеру: позиции, количества, услуги.",
            "parameters": {
                "type": "object",
                "properties": {"order_number": {"type": "string", "description": "Номер заявки"}},
                "required": ["order_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_products",
            "description": "Список товаров пользователя с остатками на складе и количеством брака.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Макс. число товаров в ответе (по умолчанию 20)."},
                    "offset": {"type": "integer", "description": "Смещение для пагинации (по умолчанию 0)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Детали товара по штрихкоду или названию.",
            "parameters": {
                "type": "object",
                "properties": {
                    "barcode": {"type": "string", "description": "Штрихкод товара"},
                    "name": {"type": "string", "description": "Часть названия товара"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_summary",
            "description": "Общая сводка по остаткам на складе и браку по всем товарам.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_shipment_requests",
            "description": "Заявки на отгрузку пользователя и их статусы.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_services_price",
            "description": "Прайс-лист услуг фулфилмента. Можно фильтровать по категории.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Фильтр по категории (опционально)."},
                    "limit": {"type": "integer", "description": "Макс. число позиций в ответе (по умолчанию 50)."},
                    "offset": {"type": "integer", "description": "Смещение для пагинации (по умолчанию 0)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_info",
            "description": "Реквизиты компании пользователя: ИНН, название, банк, расчётный счёт.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_destinations",
            "description": "Доступные адреса доставки (склады, маркетплейсы).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Макс. число адресов в ответе (по умолчанию 50)."},
                    "offset": {"type": "integer", "description": "Смещение для пагинации (по умолчанию 0)."},
                },
            },
        },
    },
]


def _normalize_order_statuses(value: str | list | None) -> list[str]:
    """Convert status string or list (with synonyms) to list of canonical statuses from DB."""
    if value is None:
        return []
    if isinstance(value, list):
        tokens = [str(s).strip() for s in value if s]
    else:
        tokens = [s.strip() for s in str(value).replace(",", " ").split() if s.strip()]
    result = []
    for t in tokens:
        lower = t.lower()
        if t in ORDER_STATUSES:
            result.append(t)
        elif lower in ORDER_STATUS_SYNONYMS:
            result.append(ORDER_STATUS_SYNONYMS[lower])
    return list(dict.fromkeys(result))


def _parse_limit_offset(arguments: dict, limit_key: str, offset_key: str, max_limit: int) -> tuple[int, int]:
    """Parse limit and offset from arguments with caps. Returns (limit, offset)."""
    limit = arguments.get(limit_key)
    offset = arguments.get(offset_key)
    try:
        limit = max(1, min(int(limit), max_limit)) if limit is not None else min(20, max_limit)
    except (TypeError, ValueError):
        limit = min(20, max_limit)
    try:
        offset = max(0, int(offset)) if offset is not None else 0
    except (TypeError, ValueError):
        offset = 0
    return limit, offset


async def _ensure_company(db: AsyncSession, user: User, company_id: int | None) -> Company | None:
    """Return company if user has access and company_id is set."""
    if company_id is None:
        return None
    if user.role in {"warehouse", "admin"}:
        result = await db.execute(select(Company).where(Company.id == company_id))
    else:
        result = await db.execute(
            select(Company).where(Company.id == company_id, Company.user_id == user.id)
        )
    return result.scalar_one_or_none()


async def execute_tool(
    name: str,
    arguments: dict,
    db: AsyncSession,
    user: User,
    company_id: int | None,
) -> str:
    """
    Execute a tool by name with given arguments. Returns JSON string for OpenAI.
    All company-scoped tools require company_id (current company in chat).
    """
    try:
        company = await _ensure_company(db, user, company_id)
    except Exception:
        logger.exception("ai_tool_ensure_company_failed", tool=name)
        return json.dumps({"error": "Временная ошибка. Попробуйте позже."})

    try:
        return await _execute_tool_impl(name, arguments, db, user, company_id, company)
    except Exception:
        logger.exception("ai_tool_execution_failed", tool=name)
        return json.dumps({"error": "Временная ошибка. Попробуйте позже."})


async def _execute_tool_impl(
    name: str,
    arguments: dict,
    db: AsyncSession,
    user: User,
    company_id: int | None,
    company: Company | None,
) -> str:
    """Implementation of tool execution. Called from execute_tool after company resolution."""
    if name == "get_orders":
        if not company:
            return json.dumps({"error": "Не указана компания. Выберите компанию в приложении."})
        base = select(Order).where(Order.company_id == company.id)
        statuses = _normalize_order_statuses(arguments.get("statuses") or arguments.get("status"))
        if statuses:
            base = base.where(Order.status.in_(statuses))
        total_result = await db.execute(select(func.count()).select_from(base.subquery()))
        total = int(total_result.scalar_one())
        limit, offset = _parse_limit_offset(arguments, "limit", "offset", MAX_ORDERS)
        q = base.order_by(Order.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(q)
        orders = result.scalars().all()
        items = [
            {
                "order_number": o.order_number,
                "status": o.status,
                "destination": o.destination,
                "planned_qty": o.planned_qty,
                "received_qty": o.received_qty,
                "packed_qty": o.packed_qty,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ]
        out = {
            "items": items,
            "total": total,
            "has_more": offset + len(items) < total,
            "next_offset": offset + len(items) if offset + len(items) < total else None,
        }
        return json.dumps(out, ensure_ascii=False)

    if name == "get_order_details":
        if not company:
            return json.dumps({"error": "Не указана компания. Выберите компанию в приложении."})
        order_number = (arguments.get("order_number") or "").strip()
        if not order_number:
            return json.dumps({"error": "Укажите номер заявки."})
        order_result = await db.execute(
            select(Order).where(Order.company_id == company.id, Order.order_number == order_number)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            return json.dumps({"error": f"Заявка с номером {order_number} не найдена."})
        items_result = await db.execute(
            select(OrderItem, Product)
            .join(Product, Product.id == OrderItem.product_id)
            .where(OrderItem.order_id == order.id)
        )
        items = [
            {
                "product_name": p.name,
                "barcode": p.barcode,
                "planned_qty": i.planned_qty,
                "received_qty": i.received_qty,
                "packed_qty": i.packed_qty,
                "defect_qty": i.defect_qty,
            }
            for i, p in items_result.all()
        ]
        svc_result = await db.execute(
            select(OrderService, Service)
            .join(Service, Service.id == OrderService.service_id)
            .where(OrderService.order_id == order.id)
        )
        services = [
            {"name": s.name, "quantity": float(os.quantity), "price_at_order": float(os.price_at_order)}
            for os, s in svc_result.all()
        ]
        out = {
            "order_number": order.order_number,
            "status": order.status,
            "destination": order.destination,
            "planned_qty": order.planned_qty,
            "received_qty": order.received_qty,
            "packed_qty": order.packed_qty,
            "items": items,
            "services": services,
        }
        return json.dumps(out, ensure_ascii=False)

    if name == "get_products":
        if not company:
            return json.dumps({"error": "Не указана компания. Выберите компанию в приложении."})
        base = select(Product).where(Product.company_id == company.id)
        total_result = await db.execute(select(func.count()).select_from(base.subquery()))
        total = int(total_result.scalar_one())
        limit, offset = _parse_limit_offset(arguments, "limit", "offset", MAX_PRODUCTS)
        result = await db.execute(base.order_by(Product.name).offset(offset).limit(limit))
        products = result.scalars().all()
        items = [
            {
                "name": p.name,
                "brand": p.brand,
                "barcode": p.barcode,
                "stock_quantity": p.stock_quantity,
                "defect_quantity": p.defect_quantity,
            }
            for p in products
        ]
        out = {
            "items": items,
            "total": total,
            "has_more": offset + len(items) < total,
            "next_offset": offset + len(items) if offset + len(items) < total else None,
        }
        return json.dumps(out, ensure_ascii=False)

    if name == "get_product_details":
        if not company:
            return json.dumps({"error": "Не указана компания. Выберите компанию в приложении."})
        barcode = (arguments.get("barcode") or "").strip()
        name_part = (arguments.get("name") or "").strip()
        if barcode:
            result = await db.execute(
                select(Product).where(Product.company_id == company.id, Product.barcode == barcode)
            )
        elif name_part:
            result = await db.execute(
                select(Product)
                .where(Product.company_id == company.id, Product.name.ilike(f"%{name_part}%"))
                .limit(10)
            )
        else:
            return json.dumps({"error": "Укажите штрихкод или название товара."})
        products = result.scalars().all()
        out = [
            {
                "name": p.name,
                "brand": p.brand,
                "size": p.size,
                "color": p.color,
                "barcode": p.barcode,
                "wb_article": p.wb_article,
                "stock_quantity": p.stock_quantity,
                "defect_quantity": p.defect_quantity,
                "packing_instructions": p.packing_instructions,
            }
            for p in products
        ]
        return json.dumps(out, ensure_ascii=False)

    if name == "get_stock_summary":
        if not company:
            return json.dumps({"error": "Не указана компания. Выберите компанию в приложении."})
        result = await db.execute(
            select(
                func.coalesce(func.sum(Product.stock_quantity), 0),
                func.coalesce(func.sum(Product.defect_quantity), 0),
                func.count(Product.id),
            ).where(Product.company_id == company.id)
        )
        row = result.one()
        total_stock = int(row[0])
        total_defect = int(row[1])
        count = int(row[2])
        defect_count_result = await db.execute(
            select(func.count()).select_from(Product).where(
                Product.company_id == company.id, Product.defect_quantity > 0
            )
        )
        total_defect_items = int(defect_count_result.scalar_one())
        defect_result = await db.execute(
            select(Product.name, Product.defect_quantity)
            .where(Product.company_id == company.id, Product.defect_quantity > 0)
            .order_by(Product.defect_quantity.desc())
            .limit(MAX_DEFECT_ITEMS)
        )
        defect_list = [{"name": n, "defect_quantity": q} for n, q in defect_result.all()]
        out = {
            "total_products": count,
            "total_stock_quantity": total_stock,
            "total_defect_quantity": total_defect,
            "total_defect_items": total_defect_items,
            "products_with_defects": defect_list,
        }
        return json.dumps(out, ensure_ascii=False)

    if name == "get_shipment_requests":
        if not company:
            return json.dumps({"error": "Не указана компания. Выберите компанию в приложении."})
        result = await db.execute(
            select(ShipmentRequest)
            .where(ShipmentRequest.company_id == company.id)
            .order_by(ShipmentRequest.created_at.desc())
            .limit(MAX_SHIPMENT_REQUESTS)
        )
        requests = result.scalars().all()
        out = [
            {
                "id": r.id,
                "destination_type": r.destination_type,
                "status": r.status,
                "destination_comment": r.destination_comment,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in requests
        ]
        return json.dumps(out, ensure_ascii=False)

    if name == "get_services_price":
        base = select(Service).where(Service.is_active.is_(True))
        if arguments.get("category"):
            base = base.where(Service.category.ilike(f"%{arguments['category']}%"))
        total_result = await db.execute(select(func.count()).select_from(base.subquery()))
        total = int(total_result.scalar_one())
        limit, offset = _parse_limit_offset(arguments, "limit", "offset", MAX_SERVICES)
        q = base.order_by(Service.category, Service.sort_order, Service.name).offset(offset).limit(limit)
        result = await db.execute(q)
        services = result.scalars().all()
        items = [
            {"category": s.category, "name": s.name, "price": float(s.price), "unit": s.unit}
            for s in services
        ]
        out = {
            "items": items,
            "total": total,
            "has_more": offset + len(items) < total,
            "next_offset": offset + len(items) if offset + len(items) < total else None,
        }
        return json.dumps(out, ensure_ascii=False)

    if name == "get_company_info":
        if not company:
            return json.dumps({"error": "Не указана компания. Выберите компанию в приложении."})
        out = {
            "name": company.name,
            "inn": company.inn,
            "kpp": company.kpp,
            "ogrn": company.ogrn,
            "legal_address": company.legal_address,
            "director": company.director,
            "bank_name": company.bank_name,
            "bank_bik": company.bank_bik,
            "bank_account": company.bank_account,
            "bank_corr_account": company.bank_corr_account,
        }
        return json.dumps(out, ensure_ascii=False)

    if name == "get_destinations":
        base = select(Destination).where(Destination.is_active.is_(True))
        total_result = await db.execute(select(func.count()).select_from(base.subquery()))
        total = int(total_result.scalar_one())
        limit, offset = _parse_limit_offset(arguments, "limit", "offset", MAX_DESTINATIONS)
        result = await db.execute(base.order_by(Destination.name).offset(offset).limit(limit))
        dests = result.scalars().all()
        items = [{"id": d.id, "name": d.name} for d in dests]
        out = {
            "items": items,
            "total": total,
            "has_more": offset + len(items) < total,
            "next_offset": offset + len(items) if offset + len(items) < total else None,
        }
        return json.dumps(out, ensure_ascii=False)

    return json.dumps({"error": f"Неизвестная функция: {name}"})
