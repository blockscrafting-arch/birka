"""Tests for AI tools."""
import json

from app.db.models.company import Company
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
