"""Companies tests."""


async def test_create_company(client, auth_headers):
    payload = {"inn": "1234567890"}
    response = await client.post("/api/v1/companies", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["inn"] == "1234567890"
