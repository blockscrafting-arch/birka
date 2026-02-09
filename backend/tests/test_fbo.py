"""Tests for FBO sync with mocked Ozon API."""
import respx
import httpx
import pytest


OZON_BASE = "https://api-seller.ozon.ru"


@pytest.mark.asyncio
async def test_fbo_sync_ozon_requires_ozon_article(client, auth_headers):
    """Sync Ozon supply fails with clear error when product has no ozon_article."""
    cr = await client.post("/api/v1/companies", json={"inn": "6666666666"}, headers=auth_headers)
    assert cr.status_code == 200
    company_id = cr.json()["id"]

    # Product without ozon_article
    pr = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Test", "ozon_article": None},
        headers=auth_headers,
    )
    assert pr.status_code == 200
    product_id = pr.json()["id"]

    # Create Ozon supply
    sup = await client.post(
        "/api/v1/fbo/supplies",
        json={
            "company_id": company_id,
            "marketplace": "ozon",
            "boxes": [{"box_number": 1, "items": [{"product_id": product_id, "quantity": 1}]}],
        },
        headers=auth_headers,
    )
    assert sup.status_code == 200
    supply_id = sup.json()["id"]

    # Sync without mocking Ozon: should fail with 400 (ozon_article missing)
    r = await client.post(f"/api/v1/fbo/supplies/{supply_id}/sync", headers=auth_headers)
    assert r.status_code == 400
    assert "артикул Ozon" in r.json().get("detail", "")


@pytest.mark.asyncio
async def test_fbo_sync_ozon_success_with_mocks(client, auth_headers):
    """Sync Ozon supply succeeds when Ozon API is mocked; external_supply_id and external_box_id are set."""
    cr = await client.post("/api/v1/companies", json={"inn": "7777777777"}, headers=auth_headers)
    assert cr.status_code == 200
    company_id = cr.json()["id"]

    await client.put(
        f"/api/v1/companies/{company_id}/api-keys",
        json={"ozon_client_id": "c", "ozon_api_key": "k"},
        headers=auth_headers,
    )

    pr = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Prod", "ozon_article": "ART-OZON"},
        headers=auth_headers,
    )
    assert pr.status_code == 200
    product_id = pr.json()["id"]

    sup = await client.post(
        "/api/v1/fbo/supplies",
        json={
            "company_id": company_id,
            "marketplace": "ozon",
            "boxes": [{"box_number": 1, "items": [{"product_id": product_id, "quantity": 2}]}],
        },
        headers=auth_headers,
    )
    assert sup.status_code == 200
    supply_id = sup.json()["id"]

    with respx.mock:
        respx.post(f"{OZON_BASE}/v3/product/info/list").mock(
            return_value=httpx.Response(
                200,
                json={"result": {"items": [{"offer_id": "ART-OZON", "sku": 99999}]}},
            )
        )
        respx.post(f"{OZON_BASE}/v1/draft/create").mock(
            return_value=httpx.Response(200, json={"operation_id": "op-draft"})
        )
        respx.post(f"{OZON_BASE}/v1/draft/create/info").mock(
            return_value=httpx.Response(
                200,
                json={
                    "result": {
                        "status": "SUCCESS",
                        "draft_id": 100,
                        "warehouse_id": 200,
                        "timeslots": [
                            {"from_in_timezone": "2025-12-01T09:00:00Z", "to_in_timezone": "2025-12-01T18:00:00Z"},
                        ],
                    }
                },
            )
        )
        respx.post(f"{OZON_BASE}/v1/draft/supply/create").mock(
            return_value=httpx.Response(200, json={"operation_id": "op-supply"})
        )
        respx.post(f"{OZON_BASE}/v1/supply/create/status").mock(
            return_value=httpx.Response(
                200,
                json={"status": "DraftSupplyCreateStatusSuccess", "result": {"order_ids": ["42"]}},
            )
        )
        respx.post(f"{OZON_BASE}/v1/cargoes/create").mock(
            return_value=httpx.Response(200, json={"operation_id": "op-cargo"})
        )
        respx.post(f"{OZON_BASE}/v2/cargoes/create/info").mock(
            return_value=httpx.Response(
                200,
                json={
                    "result": {
                        "status": "SUCCESS",
                        "cargoes": [{"cargo_id": "cargo-1"}],
                    }
                },
            )
        )

        r = await client.post(f"/api/v1/fbo/supplies/{supply_id}/sync", headers=auth_headers)
        assert r.status_code == 200, r.json()
        data = r.json()
        assert data.get("external_supply_id") == "42"
        assert data.get("status") == "active"
        boxes = data.get("boxes") or []
        assert len(boxes) >= 1
        assert boxes[0].get("external_box_id") == "cargo-1"
