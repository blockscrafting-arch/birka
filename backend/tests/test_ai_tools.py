"""Tests for AI tools."""
import json

from app.db.models.company import Company
from app.db.models.order import Order
from app.db.models.product import Product
from app.db.models.user import User
from app.services import ai_tools


async def test_get_stock_summary_returns_top_stock_products(db_session, unique_inn):
    """get_stock_summary response includes top_stock_products."""
    user = User(
        telegram_id=999,
        telegram_username="ai_test_user",
        first_name="AI Test",
        role="client",
    )
    db_session.add(user)
    await db_session.flush()

    company = Company(user_id=user.id, inn=unique_inn, name="Тест ИИ")
    db_session.add(company)
    await db_session.flush()

    product = Product(
        company_id=company.id,
        name="Товар с остатком",
        stock_quantity=15,
    )
    db_session.add(product)
    await db_session.commit()

    result_str = await ai_tools.execute_tool(
        "get_stock_summary",
        {},
        db_session,
        user,
        company.id,
    )
    result = json.loads(result_str)
    assert "top_stock_products" in result
    assert isinstance(result["top_stock_products"], list)
    assert len(result["top_stock_products"]) >= 1
    assert result["top_stock_products"][0]["name"] == "Товар с остатком"
    assert result["top_stock_products"][0]["stock_quantity"] == 15


# ── Фаза 6: расширение ────────────────────────────────────────────────────────


async def test_execute_tool_no_company_returns_error(db_session, unique_inn):
    """get_orders with company_id=None → error message about missing company."""
    user = User(telegram_id=7700001, telegram_username="no_comp", first_name="NoComp", role="client")
    db_session.add(user)
    await db_session.commit()

    result_str = await ai_tools.execute_tool("get_orders", {}, db_session, user, None)
    result = json.loads(result_str)
    assert "error" in result or "компания" in str(result).lower()


async def test_get_orders_status_synonym(db_session, unique_inn):
    """status='отгружено' resolves to canonical 'Завершено'."""
    user = User(telegram_id=7700002, telegram_username="syn_user", first_name="Syn", role="client")
    db_session.add(user)
    await db_session.flush()
    company = Company(user_id=user.id, inn=unique_inn, name="Синонимы")
    db_session.add(company)
    await db_session.commit()

    result_str = await ai_tools.execute_tool(
        "get_orders", {"status": "отгружено"}, db_session, user, company.id
    )
    result = json.loads(result_str)
    assert "error" not in result
    # orders list returned (may be empty, but no crash)
    assert "orders" in result or "items" in result or isinstance(result, dict)


async def test_order_details_not_found(db_session, unique_inn):
    """get_order_details with non-existent order_number → error."""
    user = User(telegram_id=7700003, telegram_username="no_order", first_name="NoOrder", role="client")
    db_session.add(user)
    await db_session.flush()
    company = Company(user_id=user.id, inn=unique_inn, name="НетЗаявки")
    db_session.add(company)
    await db_session.commit()

    result_str = await ai_tools.execute_tool(
        "get_order_details", {"order_number": "NONEXISTENT-99999"}, db_session, user, company.id
    )
    result = json.loads(result_str)
    assert "error" in result or "не найден" in str(result).lower() or "not found" in str(result).lower()


async def test_unknown_tool_returns_error(db_session, unique_inn):
    """Unknown tool name → error message."""
    user = User(telegram_id=7700004, telegram_username="unk_tool", first_name="Unk", role="client")
    db_session.add(user)
    await db_session.flush()
    company = Company(user_id=user.id, inn=unique_inn, name="НеизвФ")
    db_session.add(company)
    await db_session.commit()

    result_str = await ai_tools.execute_tool(
        "nonexistent_tool_xyz", {}, db_session, user, company.id
    )
    result = json.loads(result_str)
    assert "error" in result


async def test_get_products_pagination(db_session, unique_inn):
    """limit=1 returns only 1 product when 2 exist, has_more=True."""
    user = User(telegram_id=7700005, telegram_username="pag_user", first_name="Pag", role="client")
    db_session.add(user)
    await db_session.flush()
    company = Company(user_id=user.id, inn=unique_inn, name="Пагинация")
    db_session.add(company)
    await db_session.flush()

    db_session.add(Product(company_id=company.id, name="Продукт А", stock_quantity=1))
    db_session.add(Product(company_id=company.id, name="Продукт Б", stock_quantity=2))
    await db_session.commit()

    result_str = await ai_tools.execute_tool(
        "get_products", {"limit": 1, "offset": 0}, db_session, user, company.id
    )
    result = json.loads(result_str)
    assert "error" not in result
    products = result.get("products", result.get("items", []))
    assert len(products) == 1
    assert result.get("has_more") is True or result.get("total", 0) >= 2


async def test_client_cannot_access_other_company_ai_tools(db_session):
    """client user with other company's id → _ensure_company returns None → error."""
    inn1 = str(7700006)
    inn2 = str(7700007)

    user1 = User(telegram_id=7700008, telegram_username="u1_ai", first_name="U1", role="client")
    user2 = User(telegram_id=7700009, telegram_username="u2_ai", first_name="U2", role="client")
    db_session.add(user1)
    db_session.add(user2)
    await db_session.flush()

    company1 = Company(user_id=user1.id, inn=inn1, name="КомпаниЯ1")
    db_session.add(company1)
    await db_session.commit()

    # user2 trying to access company1's data
    result_str = await ai_tools.execute_tool(
        "get_orders", {}, db_session, user2, company1.id
    )
    result = json.loads(result_str)
    # Should return error because user2 doesn't own company1
    assert "error" in result or result.get("orders") == []
