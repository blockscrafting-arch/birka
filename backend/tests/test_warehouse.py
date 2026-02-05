"""Warehouse tests."""


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


async def test_packing_record_updates_order_and_item_packed_qty(client, auth_headers, warehouse_headers):
    """Creating a packing record updates order.packed_qty and the matching OrderItem.packed_qty."""
    company_resp = await client.post("/api/v1/companies", json={"inn": "1112223330"}, headers=auth_headers)
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


async def test_packing_forbidden_before_receiving(client, auth_headers, warehouse_headers):
    """Packing is rejected with 400 when order has not been received yet."""
    company_resp = await client.post("/api/v1/companies", json={"inn": "1112223331"}, headers=auth_headers)
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


async def test_packing_updates_correct_order_item(client, auth_headers, warehouse_headers):
    """When same product appears in two lines (e.g. different destinations), packing updates the selected line."""
    company_resp = await client.post("/api/v1/companies", json={"inn": "1112223332"}, headers=auth_headers)
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


async def test_overpack_rejected(client, auth_headers, warehouse_headers):
    """Packing more than (received - defect - already packed) for the line returns 400."""
    company_resp = await client.post("/api/v1/companies", json={"inn": "1112223333"}, headers=auth_headers)
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


async def test_packing_status_flow_and_complete(client, auth_headers, warehouse_headers):
    """Packing sets Упаковка or Готово к отгрузке; only complete_order sets Завершено."""
    company_resp = await client.post("/api/v1/companies", json={"inn": "1112223334"}, headers=auth_headers)
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
