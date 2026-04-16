"""Orders tests."""
import io
from unittest.mock import AsyncMock, patch

import pandas as pd



async def test_create_order(client, auth_headers, unique_inn):
    company = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
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


async def test_order_export(client, auth_headers, unique_inn):
    """Export order items returns xlsx file."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар для экспорта"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]

    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    response = await client.get(f"/api/v1/orders/{order_id}/export", headers=auth_headers)
    assert response.status_code == 200
    assert "spreadsheet" in response.headers.get("content-type", "")
    buf = io.BytesIO(response.content)
    df = pd.read_excel(buf)
    assert "Название" in df.columns
    assert "Количество" in df.columns
    assert len(df) >= 1
    assert list(df["Количество"])[0] == 5


async def test_order_import(client, auth_headers, unique_inn):
    """Import order from Excel creates order with items."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    df = pd.DataFrame(
        [{"Название": "Импортный товар", "Количество": 7}],
        columns=["Название", "Количество"],
    )
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    files = {"file": ("import.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

    response = await client.post(
        f"/api/v1/orders/import?company_id={company_id}",
        files=files,
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == company_id
    assert "id" in data

    items_resp = await client.get(f"/api/v1/orders/{data['id']}/items", headers=auth_headers)
    assert items_resp.status_code == 200
    items = items_resp.json()
    assert len(items) == 1
    assert items[0]["planned_qty"] == 7
    assert "Импортный товар" in (items[0].get("product_name") or "")


async def test_order_import_missing_columns(client, auth_headers, unique_inn):
    """Import with Excel missing required columns returns 400."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    df = pd.DataFrame([{"Другой столбец": "значение"}])
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    files = {"file": ("bad.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

    response = await client.post(
        f"/api/v1/orders/import?company_id={company_id}",
        files=files,
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "столбц" in response.json().get("detail", "").lower() or "Название" in response.json().get("detail", "")


async def test_send_import_template_to_telegram(client, auth_headers_and_user):
    """POST /orders/import/template/send sends template to current user in Telegram."""
    headers, user = auth_headers_and_user
    with patch("app.api.v1.routes.orders.send_document", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        response = await client.post("/api/v1/orders/import/template/send", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"sent": True}
    mock_send.assert_called_once()
    call_args = mock_send.call_args[0]
    assert call_args[0] == user.telegram_id
    assert call_args[2] == "Шаблон_заявки.xlsx"
    assert len(call_args[1]) > 100  # Excel buffer


async def test_send_import_template_no_telegram_returns_400(client):
    """POST /orders/import/template/send returns 400 when current user has no telegram_id."""
    from app.api.v1.deps import get_current_user
    from app.main import app

    class UserNoTelegram:
        id = 1
        role = "client"
        telegram_id = None

    async def mock_get_current_user():
        return UserNoTelegram()

    app.dependency_overrides[get_current_user] = mock_get_current_user
    try:
        response = await client.post(
            "/api/v1/orders/import/template/send",
            headers={"X-Session-Token": "any"},  # override ignores real auth
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 400
    assert "Telegram" in response.json().get("detail", "")


async def test_update_order_status_client_forbidden(client, auth_headers, unique_inn):
    """Client cannot PATCH order status; only warehouse/admin can."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]
    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]
    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "Принято"},
        headers=auth_headers,
    )
    assert response.status_code == 403
    assert "Доступ запрещён" in response.json().get("detail", "") or "forbidden" in response.json().get("detail", "").lower()


async def test_update_order_status_invalid_transition(client, auth_headers, warehouse_headers, unique_inn):
    """PATCH with disallowed transition (e.g. На приемке -> Завершено) returns 400."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]
    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]
    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]
    assert order_resp.json()["status"] == "На приемке"

    response = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "Завершено"},
        headers=warehouse_headers,
    )
    assert response.status_code == 400
    assert "Недопустимый переход" in response.json().get("detail", "") or "статус" in response.json().get("detail", "").lower()


async def test_update_order_status_allowed_transition(client, auth_headers, warehouse_headers, unique_inn):
    """Warehouse can PATCH status when transition is allowed (e.g. На приемке -> Принято)."""
    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=auth_headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]
    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Товар"},
        headers=auth_headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]
    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 5}]},
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    order_id = order_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "Принято"},
        headers=warehouse_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Принято"
