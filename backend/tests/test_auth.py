"""Auth tests."""


async def test_logout_requires_token(client):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 400


async def test_logout_success(client, auth_headers):
    response = await client.post("/api/v1/auth/logout", headers=auth_headers)
    assert response.status_code == 200
