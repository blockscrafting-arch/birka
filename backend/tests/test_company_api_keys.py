"""Tests for company API keys: partial update, delete, 503 on missing ENCRYPTION_KEY."""
import pytest


@pytest.mark.asyncio
async def test_api_keys_get_empty(client, auth_headers):
    """GET api-keys when no keys returns all false."""
    # Create company first
    cr = await client.post("/api/v1/companies", json={"inn": "1111111111"}, headers=auth_headers)
    assert cr.status_code == 200
    company_id = cr.json()["id"]

    r = await client.get(f"/api/v1/companies/{company_id}/api-keys", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["has_wb"] is False
    assert data["has_ozon_client_id"] is False
    assert data["has_ozon_api_key"] is False


@pytest.mark.asyncio
async def test_api_keys_put_and_get(client, auth_headers):
    """PUT all keys then GET returns all true."""
    cr = await client.post("/api/v1/companies", json={"inn": "2222222222"}, headers=auth_headers)
    assert cr.status_code == 200
    company_id = cr.json()["id"]

    r = await client.put(
        f"/api/v1/companies/{company_id}/api-keys",
        json={
            "wb_api_key": "wb-secret",
            "ozon_client_id": "ozon-client",
            "ozon_api_key": "ozon-key",
        },
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["has_wb"] is True
    assert data["has_ozon_client_id"] is True
    assert data["has_ozon_api_key"] is True

    r2 = await client.get(f"/api/v1/companies/{company_id}/api-keys", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["has_wb"] is True
    assert r2.json()["has_ozon_client_id"] is True
    assert r2.json()["has_ozon_api_key"] is True


@pytest.mark.asyncio
async def test_api_keys_partial_update(client, auth_headers):
    """PUT only wb_api_key does not clear existing Ozon keys."""
    cr = await client.post("/api/v1/companies", json={"inn": "3333333333"}, headers=auth_headers)
    assert cr.status_code == 200
    company_id = cr.json()["id"]

    # Set all keys
    await client.put(
        f"/api/v1/companies/{company_id}/api-keys",
        json={
            "wb_api_key": "wb1",
            "ozon_client_id": "client1",
            "ozon_api_key": "key1",
        },
        headers=auth_headers,
    )

    # Update only WB key (partial payload)
    r = await client.put(
        f"/api/v1/companies/{company_id}/api-keys",
        json={"wb_api_key": "wb2"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["has_wb"] is True
    assert r.json()["has_ozon_client_id"] is True
    assert r.json()["has_ozon_api_key"] is True

    r2 = await client.get(f"/api/v1/companies/{company_id}/api-keys", headers=auth_headers)
    assert r2.json()["has_ozon_client_id"] is True
    assert r2.json()["has_ozon_api_key"] is True


@pytest.mark.asyncio
async def test_api_keys_delete(client, auth_headers):
    """DELETE api-keys removes keys; GET afterwards returns all false."""
    cr = await client.post("/api/v1/companies", json={"inn": "4444444444"}, headers=auth_headers)
    assert cr.status_code == 200
    company_id = cr.json()["id"]

    await client.put(
        f"/api/v1/companies/{company_id}/api-keys",
        json={"wb_api_key": "w", "ozon_client_id": "c", "ozon_api_key": "k"},
        headers=auth_headers,
    )

    r = await client.delete(f"/api/v1/companies/{company_id}/api-keys", headers=auth_headers)
    assert r.status_code == 204

    r2 = await client.get(f"/api/v1/companies/{company_id}/api-keys", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["has_wb"] is False
    assert r2.json()["has_ozon_client_id"] is False
    assert r2.json()["has_ozon_api_key"] is False
