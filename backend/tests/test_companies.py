"""Companies tests."""
from unittest.mock import AsyncMock, patch


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


async def test_send_api_keys_guide_success(client, auth_headers):
    """POST /api-keys-guide/send returns 200 and sends guide to Telegram."""
    with patch("app.api.v1.routes.companies.send_notification", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        response = await client.post(
            "/api/v1/companies/api-keys-guide/send",
            headers=auth_headers,
        )
    assert response.status_code == 200
    assert response.json() == {"sent": True}
    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert call_args[0][1]  # text contains guide
    assert call_args[1].get("parse_mode") == "HTML"


async def test_send_api_keys_guide_telegram_failure(client, auth_headers):
    """When send_notification returns False, endpoint returns 502."""
    with patch("app.api.v1.routes.companies.send_notification", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = False
        response = await client.post(
            "/api/v1/companies/api-keys-guide/send",
            headers=auth_headers,
        )
    assert response.status_code == 502
    assert "detail" in response.json()


async def test_delete_company_success(client, auth_headers, unique_inn):
    """Delete company returns 200 and company is removed from list."""
    create = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert create.status_code in (200, 201)
    company_id = create.json()["id"]

    response = await client.delete(f"/api/v1/companies/{company_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json().get("deleted") is True

    list_resp = await client.get("/api/v1/companies", headers=auth_headers)
    assert list_resp.status_code == 200
    ids = [c["id"] for c in list_resp.json()["items"]]
    assert company_id not in ids


async def test_delete_company_with_active_orders(client, auth_headers, unique_inn):
    """Delete company with non-completed order returns 400."""
    create = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert create.status_code in (200, 201)
    company_id = create.json()["id"]

    product = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар"},
        headers=auth_headers,
    )
    assert product.status_code in (200, 201)
    product_id = product.json()["id"]

    order = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
        headers=auth_headers,
    )
    assert order.status_code == 200

    response = await client.delete(f"/api/v1/companies/{company_id}", headers=auth_headers)
    assert response.status_code == 400
    assert "активными" in response.json().get("detail", "")


async def test_delete_company_not_found(client, auth_headers):
    """DELETE non-existent company returns 404."""
    response = await client.delete("/api/v1/companies/99999", headers=auth_headers)
    assert response.status_code == 404
    assert "найдена" in response.json().get("detail", "").lower()


async def test_delete_company_other_user(client, auth_headers, warehouse_headers, unique_inn):
    """DELETE company belonging to another user returns 404."""
    create = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert create.status_code in (200, 201)
    company_id = create.json()["id"]

    response = await client.delete(f"/api/v1/companies/{company_id}", headers=warehouse_headers)
    assert response.status_code == 404
    assert "найдена" in response.json().get("detail", "").lower()
