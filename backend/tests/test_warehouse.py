"""Warehouse tests."""


async def test_receiving_requires_role(client, auth_headers):
    response = await client.post("/api/v1/warehouse/receiving/complete", json={"order_id": 1, "items": []}, headers=auth_headers)
    assert response.status_code == 403


async def test_barcode_validation(client, warehouse_headers):
    response = await client.post("/api/v1/warehouse/barcode/validate", json={"barcode": "0000"}, headers=warehouse_headers)
    assert response.status_code == 200
