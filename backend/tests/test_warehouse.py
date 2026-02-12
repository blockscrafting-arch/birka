"""Warehouse tests."""
from unittest.mock import AsyncMock, patch

from app.db.models.order_photo import OrderPhoto


async def test_receiving_requires_role(client, auth_headers):
    response = await client.post("/api/v1/warehouse/receiving/complete", json={"order_id": 1, "items": []}, headers=auth_headers)
    assert response.status_code == 403


async def test_barcode_validation(client, warehouse_headers):
    response = await client.post("/api/v1/warehouse/barcode/validate", json={"barcode": "0000"}, headers=warehouse_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "не найден" in data.get("message", "").lower() or "не найден" in str(data.get("message", ""))


async def test_barcode_validation_empty(client, warehouse_headers):
    response = await client.post("/api/v1/warehouse/barcode/validate", json={"barcode": ""}, headers=warehouse_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False


async def test_barcode_validate_product_found(client, auth_headers, warehouse_headers, unique_inn):
    """Validate returns product when barcode exists in products."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]
    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар с ШК", "barcode": "4601234567890"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)

    response = await client.post(
        "/api/v1/warehouse/barcode/validate",
        json={"barcode": "4601234567890"},
        headers=warehouse_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data.get("type") == "product"
    assert data.get("product", {}).get("name") == "Товар с ШК"
    assert data["product"]["barcode"] == "4601234567890"


async def test_barcode_validate_in_order_found(client, auth_headers, warehouse_headers, unique_inn):
    """Validate-in-order returns found when barcode matches order item."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]
    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар заявки", "barcode": "4601234567891"},
        headers=auth_headers,
    )
    product_id = product_resp.json()["id"]
    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
        headers=auth_headers,
    )
    order_id = order_resp.json()["id"]

    response = await client.post(
        "/api/v1/warehouse/barcode/validate-in-order",
        json={"barcode": "4601234567891", "order_id": order_id},
        headers=warehouse_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data.get("order_item", {}).get("product_name") == "Товар заявки"
    assert data["remaining_to_receive"] == 5


async def test_barcode_validate_in_order_not_found(client, auth_headers, warehouse_headers, unique_inn):
    """Validate-in-order returns found=False when barcode not in order."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]
    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар", "barcode": "4601234567892"},
        headers=auth_headers,
    )
    product_id = product_resp.json()["id"]
    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 3}]},
        headers=auth_headers,
    )
    order_id = order_resp.json()["id"]

    response = await client.post(
        "/api/v1/warehouse/barcode/validate-in-order",
        json={"barcode": "9999999999999", "order_id": order_id},
        headers=warehouse_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is False
    assert "заявке" in data.get("message", "").lower() or "не найден" in data.get("message", "").lower()


async def test_barcode_validate_in_order_order_not_found(client, warehouse_headers):
    """Validate-in-order returns found=False for non-existent order."""
    response = await client.post(
        "/api/v1/warehouse/barcode/validate-in-order",
        json={"barcode": "4601234567890", "order_id": 99999},
        headers=warehouse_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is False
    assert "заявк" in data.get("message", "").lower()


async def test_barcode_validate_box_found(client, auth_headers, warehouse_headers, unique_inn):
    """Validate returns type box when barcode matches FBO supply box."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]
    supply_resp = await client.post(
        "/api/v1/fbo/supplies",
        json={"company_id": company_id, "marketplace": "wb"},
        headers=auth_headers,
    )
    supply_id = supply_resp.json()["id"]
    await client.post(
        f"/api/v1/fbo/supplies/{supply_id}/import-barcodes",
        json={"barcodes": ["WB-BOX-12345"]},
        headers=auth_headers,
    )

    response = await client.post(
        "/api/v1/warehouse/barcode/validate",
        json={"barcode": "WB-BOX-12345"},
        headers=warehouse_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data.get("type") == "box"
    assert data.get("box", {}).get("external_barcode") == "WB-BOX-12345"
    assert data["box"]["supply_id"] == supply_id


async def test_packing_record_updates_order_and_item_packed_qty(client, auth_headers, warehouse_headers, unique_inn):
    """Creating a packing record updates order.packed_qty and the matching OrderItem.packed_qty."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Тест товар"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]

    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 10}]},
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=auth_headers)
    assert items_resp.status_code == 200
    items = items_resp.json()
    assert len(items) == 1
    order_item_id = items[0]["id"]

    receiving_resp = await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={
            "order_id": order_id,
            "items": [
                {"order_item_id": order_item_id, "received_qty": 10, "defect_qty": 0},
            ],
        },
        headers=warehouse_headers,
    )
    assert receiving_resp.status_code == 200

    packing_resp = await client.post(
        "/api/v1/warehouse/packing/record",
        json={
            "order_id": order_id,
            "order_item_id": order_item_id,
            "product_id": product_id,
            "employee_code": "EMP1",
            "quantity": 4,
        },
        headers=warehouse_headers,
    )
    assert packing_resp.status_code == 200

    list_orders_resp = await client.get(
        f"/api/v1/orders?company_id={company_id}&page=1&limit=10",
        headers=auth_headers,
    )
    assert list_orders_resp.status_code == 200
    orders = list_orders_resp.json()["items"]
    order = next((o for o in orders if o["id"] == order_id), None)
    assert order is not None
    assert order["packed_qty"] == 4

    items_after = await client.get(f"/api/v1/orders/{order_id}/items", headers=auth_headers)
    assert items_after.status_code == 200
    assert items_after.json()[0]["packed_qty"] == 4


async def test_packing_forbidden_before_receiving(client, auth_headers, warehouse_headers, unique_inn):
    """Packing is rejected with 400 when order has not been received yet."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар без приёмки"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]

    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=auth_headers)
    assert items_resp.status_code == 200
    order_item_id = items_resp.json()[0]["id"]

    packing_resp = await client.post(
        "/api/v1/warehouse/packing/record",
        json={
            "order_id": order_id,
            "order_item_id": order_item_id,
            "product_id": product_id,
            "employee_code": "EMP1",
            "quantity": 2,
        },
        headers=warehouse_headers,
    )
    assert packing_resp.status_code == 400
    assert "приёмк" in packing_resp.json().get("detail", "").lower()


async def test_receiving_complete_rejects_order_item_from_another_order(client, auth_headers, warehouse_headers, unique_inn):
    """Receiving/complete returns 400 when order_item_id belongs to a different order."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]

    order_a_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
        headers=auth_headers,
    )
    assert order_a_resp.status_code == 200
    order_a_id = order_a_resp.json()["id"]

    order_b_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 3}]},
        headers=auth_headers,
    )
    assert order_b_resp.status_code == 200
    order_b_id = order_b_resp.json()["id"]

    items_a = await client.get(f"/api/v1/orders/{order_a_id}/items", headers=auth_headers)
    assert items_a.status_code == 200
    order_item_from_a = items_a.json()[0]["id"]

    receiving_resp = await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={
            "order_id": order_b_id,
            "items": [{"order_item_id": order_item_from_a, "received_qty": 5, "defect_qty": 0}],
        },
        headers=warehouse_headers,
    )
    assert receiving_resp.status_code == 400
    detail = receiving_resp.json().get("detail", "")
    assert "не принадлежит" in detail or "не найдена" in detail


async def test_packing_updates_correct_order_item(client, auth_headers, warehouse_headers, unique_inn):
    """When same product appears in two lines (e.g. different destinations), packing updates the selected line."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Один товар две строки"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]

    order_resp = await client.post(
        "/api/v1/orders",
        json={
            "company_id": company_id,
            "items": [
                {"product_id": product_id, "planned_qty": 5, "destination": "Склад А"},
                {"product_id": product_id, "planned_qty": 3, "destination": "Склад Б"},
            ],
        },
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=auth_headers)
    assert items_resp.status_code == 200
    items = items_resp.json()
    assert len(items) == 2
    item_a_id = next(i["id"] for i in items if (i.get("destination") or "").strip() == "Склад А")
    item_b_id = next(i["id"] for i in items if (i.get("destination") or "").strip() == "Склад Б")

    receiving_resp = await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={
            "order_id": order_id,
            "items": [
                {"order_item_id": item_a_id, "received_qty": 5, "defect_qty": 0},
                {"order_item_id": item_b_id, "received_qty": 3, "defect_qty": 0},
            ],
        },
        headers=warehouse_headers,
    )
    assert receiving_resp.status_code == 200

    await client.post(
        "/api/v1/warehouse/packing/record",
        json={
            "order_id": order_id,
            "order_item_id": item_a_id,
            "product_id": product_id,
            "employee_code": "EMP2",
            "quantity": 2,
        },
        headers=warehouse_headers,
    )
    await client.post(
        "/api/v1/warehouse/packing/record",
        json={
            "order_id": order_id,
            "order_item_id": item_b_id,
            "product_id": product_id,
            "employee_code": "EMP2",
            "quantity": 1,
        },
        headers=warehouse_headers,
    )

    items_after = await client.get(f"/api/v1/orders/{order_id}/items", headers=auth_headers)
    assert items_after.status_code == 200
    by_id = {i["id"]: i for i in items_after.json()}
    assert by_id[item_a_id]["packed_qty"] == 2
    assert by_id[item_b_id]["packed_qty"] == 1


async def test_overpack_rejected(client, auth_headers, warehouse_headers, unique_inn):
    """Packing more than (received - defect - already packed) for the line returns 400."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар лимит"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]

    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=auth_headers)
    assert items_resp.status_code == 200
    order_item_id = items_resp.json()[0]["id"]

    await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={
            "order_id": order_id,
            "items": [{"order_item_id": order_item_id, "received_qty": 5, "defect_qty": 0}],
        },
        headers=warehouse_headers,
    )

    overpack_resp = await client.post(
        "/api/v1/warehouse/packing/record",
        json={
            "order_id": order_id,
            "order_item_id": order_item_id,
            "product_id": product_id,
            "employee_code": "EMP1",
            "quantity": 10,
        },
        headers=warehouse_headers,
    )
    assert overpack_resp.status_code == 400
    assert "перепаковк" in overpack_resp.json().get("detail", "").lower() or "доступно" in overpack_resp.json().get("detail", "").lower()


async def test_packing_status_flow_and_complete(client, auth_headers, warehouse_headers, unique_inn):
    """Packing sets Упаковка or Готово к отгрузке; only complete_order sets Завершено."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар статус"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]

    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 10}]},
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=auth_headers)
    assert items_resp.status_code == 200
    order_item_id = items_resp.json()[0]["id"]

    await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={
            "order_id": order_id,
            "items": [{"order_item_id": order_item_id, "received_qty": 10, "defect_qty": 0}],
        },
        headers=warehouse_headers,
    )

    await client.post(
        "/api/v1/warehouse/packing/record",
        json={
            "order_id": order_id,
            "order_item_id": order_item_id,
            "product_id": product_id,
            "employee_code": "EMP1",
            "quantity": 4,
        },
        headers=warehouse_headers,
    )
    list_resp = await client.get(f"/api/v1/orders?company_id={company_id}&page=1&limit=10", headers=auth_headers)
    order_after_partial = next((o for o in list_resp.json()["items"] if o["id"] == order_id), None)
    assert order_after_partial is not None
    assert order_after_partial["status"] == "Упаковка"
    assert order_after_partial["status"] != "Завершено"

    await client.post(
        "/api/v1/warehouse/packing/record",
        json={
            "order_id": order_id,
            "order_item_id": order_item_id,
            "product_id": product_id,
            "employee_code": "EMP1",
            "quantity": 6,
        },
        headers=warehouse_headers,
    )
    list_resp2 = await client.get(f"/api/v1/orders?company_id={company_id}&page=1&limit=10", headers=auth_headers)
    order_after_full = next((o for o in list_resp2.json()["items"] if o["id"] == order_id), None)
    assert order_after_full is not None
    assert order_after_full["status"] == "Готово к отгрузке"
    assert order_after_full["status"] != "Завершено"

    complete_resp = await client.post(
        f"/api/v1/warehouse/order/{order_id}/complete",
        headers=warehouse_headers,
    )
    assert complete_resp.status_code == 200
    list_resp3 = await client.get(f"/api/v1/orders?company_id={company_id}&page=1&limit=10", headers=auth_headers)
    order_final = next((o for o in list_resp3.json()["items"] if o["id"] == order_id), None)
    assert order_final is not None
    assert order_final["status"] == "Завершено"
    assert order_final.get("completed_at") is not None


async def test_receiving_partial(client, auth_headers, warehouse_headers, unique_inn):
    """Receiving only one of two items returns status partial and order stays На приемке."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    p1 = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар 1"},
        headers=auth_headers,
    )
    p2 = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар 2"},
        headers=auth_headers,
    )
    assert p1.status_code in (200, 201)
    assert p2.status_code in (200, 201)
    product_id_1 = p1.json()["id"]
    product_id_2 = p2.json()["id"]

    order_resp = await client.post(
        "/api/v1/orders",
        json={
            "company_id": company_id,
            "items": [
                {"product_id": product_id_1, "planned_qty": 3},
                {"product_id": product_id_2, "planned_qty": 2},
            ],
        },
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=auth_headers)
    assert items_resp.status_code == 200
    items = items_resp.json()
    assert len(items) == 2
    item_1_id = next(i["id"] for i in items if i["product_id"] == product_id_1)
    item_2_id = next(i["id"] for i in items if i["product_id"] == product_id_2)

    receiving_resp = await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={
            "order_id": order_id,
            "items": [{"order_item_id": item_1_id, "received_qty": 3, "defect_qty": 0, "adjustment_qty": 0}],
        },
        headers=warehouse_headers,
    )
    assert receiving_resp.status_code == 200
    data = receiving_resp.json()
    assert data.get("status") == "partial"
    assert data.get("remaining") == 1

    list_resp = await client.get(
        f"/api/v1/orders?company_id={company_id}&page=1&limit=10&status=На приемке",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    orders = list_resp.json()["items"]
    order = next((o for o in orders if o["id"] == order_id), None)
    assert order is not None
    assert order["status"] == "На приемке"


async def test_receiving_all_items(client, auth_headers, warehouse_headers, unique_inn):
    """Receiving all items sets order status Принято."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    p1 = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар A"},
        headers=auth_headers,
    )
    p2 = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар B"},
        headers=auth_headers,
    )
    assert p1.status_code in (200, 201)
    assert p2.status_code in (200, 201)
    product_id_1 = p1.json()["id"]
    product_id_2 = p2.json()["id"]

    order_resp = await client.post(
        "/api/v1/orders",
        json={
            "company_id": company_id,
            "items": [
                {"product_id": product_id_1, "planned_qty": 2},
                {"product_id": product_id_2, "planned_qty": 2},
            ],
        },
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=auth_headers)
    assert items_resp.status_code == 200
    items = items_resp.json()
    item_1_id = next(i["id"] for i in items if i["product_id"] == product_id_1)
    item_2_id = next(i["id"] for i in items if i["product_id"] == product_id_2)

    receiving_resp = await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={
            "order_id": order_id,
            "items": [
                {"order_item_id": item_1_id, "received_qty": 2, "defect_qty": 0, "adjustment_qty": 0},
                {"order_item_id": item_2_id, "received_qty": 2, "defect_qty": 0, "adjustment_qty": 0},
            ],
        },
        headers=warehouse_headers,
    )
    assert receiving_resp.status_code == 200
    data = receiving_resp.json()
    assert data.get("status") != "partial"
    assert "received" in data

    list_resp = await client.get(f"/api/v1/orders?company_id={company_id}&page=1&limit=10", headers=auth_headers)
    orders = list_resp.json()["items"]
    order = next((o for o in orders if o["id"] == order_id), None)
    assert order is not None
    assert order["status"] == "Принято"


async def test_receiving_defect_photo_count(client, auth_headers, warehouse_headers, db_session, unique_inn):
    """Receiving with defect_qty=3 but only 1 defect photo returns 400."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар с браком"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]

    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=auth_headers)
    assert items_resp.status_code == 200
    order_item_id = items_resp.json()[0]["id"]

    db_session.add(
        OrderPhoto(order_id=order_id, product_id=product_id, s3_key="test/defect1.jpg", photo_type="defect")
    )
    await db_session.commit()

    receiving_resp = await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={
            "order_id": order_id,
            "items": [
                {"order_item_id": order_item_id, "received_qty": 5, "defect_qty": 3, "adjustment_qty": 0},
            ],
        },
        headers=warehouse_headers,
    )
    assert receiving_resp.status_code == 400
    detail = receiving_resp.json().get("detail", "")
    assert "3" in detail and "1" in detail
    assert "фото" in detail.lower()


async def test_receiving_defect_exact_photos(client, auth_headers, warehouse_headers, db_session, unique_inn):
    """Receiving with defect_qty=2 and 2 defect photos succeeds."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар брак 2"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]

    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 4}]},
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=auth_headers)
    assert items_resp.status_code == 200
    order_item_id = items_resp.json()[0]["id"]

    db_session.add(
        OrderPhoto(order_id=order_id, product_id=product_id, s3_key="test/d1.jpg", photo_type="defect")
    )
    db_session.add(
        OrderPhoto(order_id=order_id, product_id=product_id, s3_key="test/d2.jpg", photo_type="defect")
    )
    await db_session.commit()

    receiving_resp = await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={
            "order_id": order_id,
            "items": [
                {"order_item_id": order_item_id, "received_qty": 4, "defect_qty": 2, "adjustment_qty": 0},
            ],
        },
        headers=warehouse_headers,
    )
    assert receiving_resp.status_code == 200
    data = receiving_resp.json()
    assert data.get("status") != "partial"
    assert data.get("defects") == 2


async def test_complete_order_with_expire_on_commit(
    client_expire_on_commit,
    auth_headers_expire_on_commit,
    warehouse_headers_expire_on_commit,
    unique_inn,
):
    """complete_order returns 200 and sets Завершено when session has expire_on_commit=True (production-like)."""
    client = client_expire_on_commit
    auth = auth_headers_expire_on_commit
    wh = warehouse_headers_expire_on_commit

    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар complete"},
        headers=auth,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]

    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
        headers=auth,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=auth)
    assert items_resp.status_code == 200
    order_item_id = items_resp.json()[0]["id"]

    await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={
            "order_id": order_id,
            "items": [{"order_item_id": order_item_id, "received_qty": 5, "defect_qty": 0}],
        },
        headers=wh,
    )

    await client.post(
        "/api/v1/warehouse/packing/record",
        json={
            "order_id": order_id,
            "order_item_id": order_item_id,
            "product_id": product_id,
            "employee_code": "EMP1",
            "quantity": 5,
        },
        headers=wh,
    )

    complete_resp = await client.post(
        f"/api/v1/warehouse/order/{order_id}/complete",
        headers=wh,
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json() == {"status": "ok"}

    list_resp = await client.get(f"/api/v1/orders?company_id={company_id}&page=1&limit=10", headers=auth)
    order_final = next((o for o in list_resp.json()["items"] if o["id"] == order_id), None)
    assert order_final is not None
    assert order_final["status"] == "Завершено"
    assert order_final.get("completed_at") is not None


async def test_export_fbo_send_to_current_user(client, auth_headers, warehouse_headers_and_user, unique_inn):
    """POST /warehouse/export-fbo/send sends file to current_user (warehouse), not company owner."""
    wh_headers, wh_user = warehouse_headers_and_user
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]
    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар FBO"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]
    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]
    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=auth_headers)
    assert items_resp.status_code == 200
    order_item_id = items_resp.json()[0]["id"]
    await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={"order_id": order_id, "items": [{"order_item_id": order_item_id, "received_qty": 5, "defect_qty": 0}]},
        headers=wh_headers,
    )
    await client.post(
        "/api/v1/warehouse/packing/record",
        json={
            "order_id": order_id,
            "order_item_id": order_item_id,
            "product_id": product_id,
            "employee_code": "E1",
            "quantity": 5,
        },
        headers=wh_headers,
    )
    with patch("app.api.v1.routes.warehouse.send_document", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        response = await client.post(
            f"/api/v1/warehouse/export-fbo/send?order_id={order_id}",
            headers=wh_headers,
        )
    assert response.status_code == 200
    assert response.json() == {"sent": True}
    mock_send.assert_called_once()
    call_telegram_id = mock_send.call_args[0][0]
    assert call_telegram_id == wh_user.telegram_id
    assert "FBO" in mock_send.call_args[0][2] or "Отгрузка" in mock_send.call_args[0][2]