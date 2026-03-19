"""Shipping (shipment request) tests."""


async def test_create_shipment_wb_without_api_keys_returns_400(
    client, auth_headers, warehouse_headers, unique_inn
):
    """Creating a shipment request with destination_type WB without company API keys returns 400 (validation)."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар отгрузка"},
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
    await client.post(
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

    create_resp = await client.post(
        "/api/v1/shipping",
        json={
            "company_id": company_id,
            "order_id": order_id,
            "destination_type": "WB",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 400
    detail = create_resp.json().get("detail", "")
    assert "API" in detail or "ключ" in detail.lower() or "Wildberries" in detail
