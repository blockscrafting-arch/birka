"""Companies tests."""


async def test_create_company(client, auth_headers):
    payload = {"inn": "1234567890"}
    response = await client.post("/api/v1/companies", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["inn"] == "1234567890"


async def test_bank_by_bik_invalid(client, auth_headers):
    """Invalid BIK returns 422."""
    response = await client.get(
        "/api/v1/companies/bank-by-bik?bik=12345678",
        headers=auth_headers,
    )
    assert response.status_code == 422
    response = await client.get(
        "/api/v1/companies/bank-by-bik?bik=abc",
        headers=auth_headers,
    )
    assert response.status_code == 422
