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
