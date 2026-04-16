"""Order lifecycle E2E tests."""
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select as sa_select

from app.db.models.order import Order
from app.db.models.order_counter import OrderCounter


async def _ensure_counter(db_session):
    """Pre-insert OrderCounter for SQLite (no ON CONFLICT support)."""
    today = date.today()
    existing = await db_session.execute(sa_select(OrderCounter).where(OrderCounter.counter_date == today))
    if not existing.scalar_one_or_none():
        db_session.add(OrderCounter(counter_date=today, value=0))
        await db_session.commit()


async def _setup_company_and_product(client, headers, unique_inn):
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Lifecycle товар"},
        headers=headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]
    return company_id, product_id


async def test_full_lifecycle(client, auth_headers_and_user, warehouse_headers, db_session, unique_inn):
    """Create → receive → pack → status transitions at each step."""
    headers, _user = auth_headers_and_user
    await _ensure_counter(db_session)

    with patch("app.api.v1.routes.warehouse.send_notification", new_callable=AsyncMock):
        company_id, product_id = await _setup_company_and_product(client, headers, unique_inn)

        order_resp = await client.post(
            "/api/v1/orders",
            json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
            headers=headers,
        )
        assert order_resp.status_code == 200
        order_id = order_resp.json()["id"]
        assert order_resp.json()["status"] == "На приемке"

        items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=headers)
        order_item_id = items_resp.json()[0]["id"]

        recv = await client.post(
            "/api/v1/warehouse/receiving/complete",
            json={"order_id": order_id, "items": [{"order_item_id": order_item_id, "received_qty": 5, "defect_qty": 0}]},
            headers=warehouse_headers,
        )
        assert recv.status_code == 200

        # Check status via list (no single-order GET endpoint)
        list_check = await client.get(f"/api/v1/orders?company_id={company_id}&page=1&limit=100", headers=headers)
        orders = list_check.json()["items"]
        order_obj = next(o for o in orders if o["id"] == order_id)
        assert order_obj["status"] == "Принято"

        pack = await client.post(
            "/api/v1/warehouse/packing/record",
            json={
                "order_id": order_id,
                "order_item_id": order_item_id,
                "product_id": product_id,
                "employee_code": "E1",
                "quantity": 5,
            },
            headers=warehouse_headers,
        )
        assert pack.status_code == 200

        list_final = await client.get(f"/api/v1/orders?company_id={company_id}&page=1&limit=100", headers=headers)
        order_final_obj = next(o for o in list_final.json()["items"] if o["id"] == order_id)
        assert order_final_obj["status"] == "Готово к отгрузке"


async def test_create_validates_product_company(client, auth_headers_and_user, db_session, unique_inn):
    """Product from another company → 400."""
    from itertools import count as _cnt
    _inn_extra = str(int(unique_inn) + 500000000)

    headers, _user = auth_headers_and_user
    await _ensure_counter(db_session)

    # Own company + product
    c1 = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=headers)
    company_id = c1.json()["id"]
    p1 = await client.post("/api/v1/products", json={"company_id": company_id, "name": "Мой товар"}, headers=headers)
    own_product_id = p1.json()["id"]

    # Another company's product (we create it directly in DB)
    from app.db.models.company import Company
    from app.db.models.product import Product
    from app.db.models.user import User

    other_user = User(telegram_id=8800001, telegram_username="other", first_name="Other", role="client")
    db_session.add(other_user)
    await db_session.flush()
    other_company = Company(user_id=other_user.id, inn=_inn_extra, name="Чужая")
    db_session.add(other_company)
    await db_session.flush()
    other_product = Product(company_id=other_company.id, name="Чужой товар")
    db_session.add(other_product)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": other_product.id, "planned_qty": 1}]},
        headers=headers,
    )
    assert resp.status_code in (400, 404)


async def test_create_empty_items_rejected(client, auth_headers_and_user, db_session, unique_inn):
    """items=[] → 400."""
    headers, _ = auth_headers_and_user
    await _ensure_counter(db_session)

    c = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=headers)
    company_id = c.json()["id"]

    resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": []},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_create_zero_qty_rejected(client, auth_headers_and_user, db_session, unique_inn):
    """planned_qty=0 → 400."""
    headers, _ = auth_headers_and_user
    await _ensure_counter(db_session)

    company_id, product_id = await _setup_company_and_product(client, headers, unique_inn)

    resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 0}]},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_complete_sets_completed_at(client, auth_headers_and_user, warehouse_headers, db_session, unique_inn):
    """After complete_order, completed_at is not null."""
    headers, _ = auth_headers_and_user
    await _ensure_counter(db_session)

    with patch("app.api.v1.routes.warehouse.send_notification", new_callable=AsyncMock):
        company_id, product_id = await _setup_company_and_product(client, headers, unique_inn)

        order_resp = await client.post(
            "/api/v1/orders",
            json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 2}]},
            headers=headers,
        )
        order_id = order_resp.json()["id"]
        items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=headers)
        order_item_id = items_resp.json()[0]["id"]

        await client.post(
            "/api/v1/warehouse/receiving/complete",
            json={"order_id": order_id, "items": [{"order_item_id": order_item_id, "received_qty": 2, "defect_qty": 0}]},
            headers=warehouse_headers,
        )
        await client.post(
            "/api/v1/warehouse/packing/record",
            json={"order_id": order_id, "order_item_id": order_item_id, "product_id": product_id, "employee_code": "E1", "quantity": 2},
            headers=warehouse_headers,
        )

        complete = await client.post(f"/api/v1/warehouse/order/{order_id}/complete", headers=warehouse_headers)
        assert complete.status_code == 200

    result = await db_session.execute(sa_select(Order).where(Order.id == order_id))
    order = result.scalar_one()
    assert order.completed_at is not None


async def test_notification_failure_does_not_break_receiving(client, auth_headers_and_user, warehouse_headers, db_session, unique_inn):
    """send_notification raises → receiving API still returns 200."""
    headers, _ = auth_headers_and_user
    await _ensure_counter(db_session)

    company_id, product_id = await _setup_company_and_product(client, headers, unique_inn)

    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 3}]},
        headers=headers,
    )
    order_id = order_resp.json()["id"]
    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=headers)
    order_item_id = items_resp.json()[0]["id"]

    with patch("app.api.v1.routes.warehouse.send_notification", side_effect=Exception("Telegram down")):
        resp = await client.post(
            "/api/v1/warehouse/receiving/complete",
            json={"order_id": order_id, "items": [{"order_item_id": order_item_id, "received_qty": 3, "defect_qty": 0}]},
            headers=warehouse_headers,
        )
    assert resp.status_code == 200


async def test_order_has_order_number(client, auth_headers_and_user, db_session, unique_inn):
    """Created order has a non-empty order_number."""
    headers, _ = auth_headers_and_user
    await _ensure_counter(db_session)

    company_id, product_id = await _setup_company_and_product(client, headers, unique_inn)

    resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 1}]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json().get("order_number")
