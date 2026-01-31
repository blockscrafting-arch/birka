"""Products tests."""


async def test_create_product(client, auth_headers):
    company = await client.post("/api/v1/companies", json={"inn": "5556667770"}, headers=auth_headers)
    company_id = company.json()["id"]

    payload = {"company_id": company_id, "name": "Шлем"}
    response = await client.post("/api/v1/products", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Шлем"
