"""Packing math tests — remainder = received − defect − packed."""
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.db.models.warehouse_employee import WarehouseEmployee


async def _pack(client, w_headers, order_id, order_item_id, product_id, qty, employee_code="EMP1"):
    return await client.post(
        "/api/v1/warehouse/packing/record",
        json={
            "order_id": order_id,
            "order_item_id": order_item_id,
            "product_id": product_id,
            "employee_code": employee_code,
            "quantity": qty,
        },
        headers=w_headers,
    )


async def test_packing_basic_ok(order_with_receiving, client):
    """Pack within remainder → 200."""
    ctx = order_with_receiving
    resp = await _pack(client, ctx["w_headers"], ctx["order_id"], ctx["order_item_id"], ctx["product_id"], qty=5)
    assert resp.status_code == 200


async def test_packing_zero_remainder_rejected(order_with_receiving, client):
    """Pack all, then pack 1 more → 400."""
    ctx = order_with_receiving
    r1 = await _pack(client, ctx["w_headers"], ctx["order_id"], ctx["order_item_id"], ctx["product_id"], qty=10)
    assert r1.status_code == 200

    r2 = await _pack(client, ctx["w_headers"], ctx["order_id"], ctx["order_item_id"], ctx["product_id"], qty=1)
    assert r2.status_code == 400


async def test_packing_with_defect_reduces_available(client, db_session, unique_inn, auth_headers_and_user, warehouse_headers, mock_notification):
    """received=10, defect=2 → only 8 available; pack 9 → 400."""
    from datetime import date
    from sqlalchemy import select as sa_select
    from app.db.models.order_counter import OrderCounter

    today = date.today()
    existing = await db_session.execute(sa_select(OrderCounter).where(OrderCounter.counter_date == today))
    if not existing.scalar_one_or_none():
        db_session.add(OrderCounter(counter_date=today, value=0))
        await db_session.commit()

    headers, _user = auth_headers_and_user
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=headers)
    company_id = company_resp.json()["id"]
    product_resp = await client.post(
        "/api/v1/products", json={"company_id": company_id, "name": "Дефект товар"}, headers=headers
    )
    product_id = product_resp.json()["id"]
    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 10}]},
        headers=headers,
    )
    order_id = order_resp.json()["id"]
    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=headers)
    order_item_id = items_resp.json()[0]["id"]

    # Receive with defect=2 (no defect photos needed when defect_qty=0 in receiving call)
    # But defect_qty > 0 requires photos. Use defect_qty=0 for simplicity here, then test packing logic.
    recv = await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={"order_id": order_id, "items": [{"order_item_id": order_item_id, "received_qty": 10, "defect_qty": 0}]},
        headers=warehouse_headers,
    )
    assert recv.status_code == 200

    # Update defect via direct DB to simulate packing with defect scenario
    from app.db.models.order import OrderItem
    result = await db_session.execute(select(OrderItem).where(OrderItem.id == order_item_id))
    item = result.scalar_one()
    item.defect_qty = 2
    await db_session.commit()

    # Try to pack 9 (> 10-2=8 available) → should fail
    resp = await _pack(client, warehouse_headers, order_id, order_item_id, product_id, qty=9)
    assert resp.status_code == 400
    assert "8" in resp.json().get("detail", "") or "доступно" in resp.json().get("detail", "").lower()


async def _get_order_status(client, headers, company_id, order_id):
    """Helper: get order status via list endpoint (no single-item endpoint exists)."""
    resp = await client.get(f"/api/v1/orders?company_id={company_id}&page=1&limit=100", headers=headers)
    assert resp.status_code == 200
    for o in resp.json()["items"]:
        if o["id"] == order_id:
            return o["status"]
    return None


async def test_packing_updates_status_to_packaging(order_with_receiving, client):
    """Partial pack → order status = 'Упаковка'."""
    ctx = order_with_receiving
    resp = await _pack(client, ctx["w_headers"], ctx["order_id"], ctx["order_item_id"], ctx["product_id"], qty=3)
    assert resp.status_code == 200

    status = await _get_order_status(client, ctx["headers"], ctx["company_id"], ctx["order_id"])
    assert status == "Упаковка"


async def test_packing_complete_sets_ready_status(order_with_receiving, client):
    """Pack all received qty → status = 'Готово к отгрузке'."""
    ctx = order_with_receiving
    resp = await _pack(client, ctx["w_headers"], ctx["order_id"], ctx["order_item_id"], ctx["product_id"], qty=10)
    assert resp.status_code == 200

    status = await _get_order_status(client, ctx["headers"], ctx["company_id"], ctx["order_id"])
    assert status == "Готово к отгрузке"


async def test_packing_decreases_stock(order_with_receiving, client, db_session):
    """Packing decreases product.stock_quantity."""
    from app.db.models.product import Product

    ctx = order_with_receiving
    # stock was 0 before receiving; after receiving 10 it's 10
    result = await db_session.execute(select(Product).where(Product.id == ctx["product_id"]))
    product = result.scalar_one()
    stock_before = product.stock_quantity

    pack_resp = await _pack(client, ctx["w_headers"], ctx["order_id"], ctx["order_item_id"], ctx["product_id"], qty=4)
    assert pack_resp.status_code == 200

    await db_session.refresh(product)
    assert product.stock_quantity == stock_before - 4


async def test_packing_before_receiving_rejected(client, db_session, unique_inn, auth_headers_and_user, warehouse_headers, mock_notification):
    """Order with no receiving yet → pack → 400."""
    from datetime import date
    from sqlalchemy import select as sa_select
    from app.db.models.order_counter import OrderCounter

    today = date.today()
    existing = await db_session.execute(sa_select(OrderCounter).where(OrderCounter.counter_date == today))
    if not existing.scalar_one_or_none():
        db_session.add(OrderCounter(counter_date=today, value=0))
        await db_session.commit()

    headers, _user = auth_headers_and_user
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=headers)
    company_id = company_resp.json()["id"]
    product_resp = await client.post(
        "/api/v1/products", json={"company_id": company_id, "name": "Без приёмки"}, headers=headers
    )
    product_id = product_resp.json()["id"]
    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
        headers=headers,
    )
    order_id = order_resp.json()["id"]
    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=headers)
    order_item_id = items_resp.json()[0]["id"]

    resp = await _pack(client, warehouse_headers, order_id, order_item_id, product_id, qty=1)
    assert resp.status_code == 400


async def test_packing_employee_auto_created(order_with_receiving, client, db_session):
    """New employee_code → WarehouseEmployee created automatically."""
    ctx = order_with_receiving
    unique_code = "AUTO_EMP_XYZ"
    resp = await _pack(client, ctx["w_headers"], ctx["order_id"], ctx["order_item_id"], ctx["product_id"], qty=1, employee_code=unique_code)
    assert resp.status_code == 200

    result = await db_session.execute(select(WarehouseEmployee).where(WarehouseEmployee.employee_code == unique_code))
    emp = result.scalar_one_or_none()
    assert emp is not None
