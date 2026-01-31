"""Orders tests."""


async def test_create_order(client, auth_headers):
    company = await client.post("/api/v1/companies", json={"inn": "1112223330"}, headers=auth_headers)
    company_id = company.json()["id"]
    product = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Перчатки"},
        headers=auth_headers,
    )
    product_id = product.json()["id"]

    payload = {"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 10}]}
    response = await client.post("/api/v1/orders", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == company_id
