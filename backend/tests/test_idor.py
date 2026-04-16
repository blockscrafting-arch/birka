"""IDOR / company isolation tests."""
from datetime import date

import pytest
from sqlalchemy import select as sa_select

from app.db.models.order_counter import OrderCounter


async def _ensure_counter(db_session):
    today = date.today()
    existing = await db_session.execute(sa_select(OrderCounter).where(OrderCounter.counter_date == today))
    if not existing.scalar_one_or_none():
        db_session.add(OrderCounter(counter_date=today, value=0))
        await db_session.commit()


async def test_client_cannot_see_other_company_products(
    client, auth_headers_and_user, second_auth_headers_and_user, unique_inn
):
    """user2 cannot list products of user1's company."""
    headers1, _ = auth_headers_and_user
    headers2, _ = second_auth_headers_and_user
    inn2 = str(int(unique_inn) + 300000001)

    c1 = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=headers1)
    company1_id = c1.json()["id"]
    await client.post("/api/v1/products", json={"company_id": company1_id, "name": "Чужой"}, headers=headers1)

    resp = await client.get(f"/api/v1/products?company_id={company1_id}", headers=headers2)
    assert resp.status_code in (403, 404)


async def test_client_cannot_update_other_company_product(
    client, auth_headers_and_user, second_auth_headers_and_user, db_session, unique_inn
):
    """user2 cannot PATCH a product belonging to user1."""
    from app.db.models.company import Company
    from app.db.models.product import Product

    headers1, user1 = auth_headers_and_user
    headers2, _ = second_auth_headers_and_user

    c1 = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=headers1)
    company1_id = c1.json()["id"]
    p1 = await client.post("/api/v1/products", json={"company_id": company1_id, "name": "Защищён"}, headers=headers1)
    product_id = p1.json()["id"]

    resp = await client.patch(
        f"/api/v1/products/{product_id}",
        json={"name": "Взлом"},
        headers=headers2,
    )
    assert resp.status_code in (403, 404)


async def test_ai_history_other_company_denied(
    client, auth_headers_and_user, second_auth_headers_and_user, unique_inn
):
    """user2 cannot read AI history for user1's company."""
    headers1, _ = auth_headers_and_user
    headers2, _ = second_auth_headers_and_user

    c1 = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=headers1)
    company1_id = c1.json()["id"]

    resp = await client.get(f"/api/v1/ai/history?company_id={company1_id}", headers=headers2)
    assert resp.status_code in (403, 404)


async def test_ai_admin_can_access_any_company(
    client, admin_headers, auth_headers_and_user, unique_inn
):
    """admin can read AI history for any company."""
    headers, _ = auth_headers_and_user
    c = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=headers)
    company_id = c.json()["id"]

    resp = await client.get(f"/api/v1/ai/history?company_id={company_id}", headers=admin_headers)
    assert resp.status_code in (200,)


async def test_warehouse_can_access_any_products(
    client, warehouse_headers, auth_headers_and_user, unique_inn
):
    """warehouse role can list products of any company."""
    headers, _ = auth_headers_and_user
    c = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=headers)
    company_id = c.json()["id"]

    resp = await client.get(f"/api/v1/products?company_id={company_id}", headers=warehouse_headers)
    assert resp.status_code == 200


async def test_ai_chat_other_company_denied(
    client, auth_headers_and_user, second_auth_headers_and_user, unique_inn
):
    """user2 cannot post to AI chat with user1's company_id."""
    from unittest.mock import AsyncMock, patch

    headers1, _ = auth_headers_and_user
    headers2, _ = second_auth_headers_and_user

    c1 = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=headers1)
    company1_id = c1.json()["id"]

    with patch("app.api.v1.routes.ai.OpenAIService") as mock_svc:
        mock_svc.return_value.chat_with_tools = AsyncMock(return_value=("Ответ", []))
        resp = await client.post(
            "/api/v1/ai/chat",
            json={"company_id": company1_id, "message": "Привет"},
            headers=headers2,
        )
    assert resp.status_code in (403, 404)
