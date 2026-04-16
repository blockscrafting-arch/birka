"""Services (pricing) and calculator tests."""
import pytest


@pytest.mark.asyncio
async def test_import_services_large_file_returns_413(client, admin_headers):
    """Import with file larger than MAX_UPLOAD_SIZE_BYTES returns 413."""
    from app.core.config import settings
    big = b"x" * (settings.MAX_UPLOAD_SIZE_BYTES + 1)
    response = await client.post(
        "/api/v1/services/import",
        headers=admin_headers,
        files={"file": ("big.xlsx", big, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 413
    assert "большой" in response.json().get("detail", "")


async def test_calculate_empty_items(client, auth_headers):
    """Empty items list returns 422 (validation)."""
    response = await client.post(
        "/api/v1/services/calculate",
        json={"items": []},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_calculate_invalid_service_id(client, auth_headers):
    """Non-existent service_id returns 400."""
    response = await client.post(
        "/api/v1/services/calculate",
        json={"items": [{"service_id": 99999, "quantity": 1}]},
        headers=auth_headers,
    )
    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert "не найдена" in detail or "неактивна" in detail or "not found" in detail.lower() or "inactive" in detail.lower()


async def test_calculate_precision(client, auth_headers, db_session, admin_headers):
    """Calculation rounds to 2 decimal places (e.g. 3.33 * 3 = 9.99)."""
    create = await client.post(
        "/api/v1/services",
        json={
            "category": "Test",
            "name": "Unit service",
            "price": "3.33",
            "unit": "шт",
        },
        headers=admin_headers,
    )
    assert create.status_code == 200
    service_id = create.json()["id"]

    response = await client.post(
        "/api/v1/services/calculate",
        json={"items": [{"service_id": service_id, "quantity": 3}]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == "9.99"
    assert len(data["items"]) == 1
    assert data["items"][0]["subtotal"] == "9.99"


async def test_calculate_inactive_service(client, auth_headers, db_session, admin_headers):
    """Inactive service returns 400."""
    create = await client.post(
        "/api/v1/services",
        json={
            "category": "Test",
            "name": "Inactive service",
            "price": "10",
            "unit": "шт",
            "is_active": False,
        },
        headers=admin_headers,
    )
    assert create.status_code == 200
    service_id = create.json()["id"]

    response = await client.post(
        "/api/v1/services/calculate",
        json={"items": [{"service_id": service_id, "quantity": 1}]},
        headers=auth_headers,
    )
    assert response.status_code == 400
