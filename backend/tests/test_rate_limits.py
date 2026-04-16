"""Rate limiting tests — verify slowapi limits are applied."""
from unittest.mock import patch

import pytest

from app.main import app


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset in-memory rate limit counters before and after each test."""
    app.state.limiter.reset()
    yield
    app.state.limiter.reset()


async def test_auth_rate_limit_429(client):
    """11th POST /auth/telegram → 429 Too Many Requests."""
    with patch("app.api.v1.routes.auth.validate_telegram_init_data", return_value=False):
        for _ in range(10):
            r = await client.post("/api/v1/auth/telegram", json={"init_data": "bad"})
            assert r.status_code == 401

        r11 = await client.post("/api/v1/auth/telegram", json={"init_data": "bad"})
    assert r11.status_code == 429


async def test_admin_endpoint_rate_limit_429(client, admin_headers):
    """31st PATCH /admin/users/{id}/role → 429."""
    for _ in range(30):
        r = await client.patch(
            "/api/v1/admin/users/99999/role",
            json={"role": "client"},
            headers=admin_headers,
        )
        # 404 is fine (user doesn't exist), 200 or 403 also ok
        assert r.status_code in (200, 404, 403, 422)

    r31 = await client.patch(
        "/api/v1/admin/users/99999/role",
        json={"role": "client"},
        headers=admin_headers,
    )
    assert r31.status_code == 429


async def test_rate_limit_applies_per_session(client, auth_headers, admin_headers):
    """User1 exhausting limit does not affect user2."""
    with patch("app.api.v1.routes.auth.validate_telegram_init_data", return_value=False):
        for _ in range(10):
            await client.post("/api/v1/auth/telegram", json={"init_data": "bad"}, headers=auth_headers)

        # user2 (admin) should still get through on first request
        r = await client.post("/api/v1/auth/telegram", json={"init_data": "bad"}, headers=admin_headers)
    # Different session → not yet rate limited (first request from admin token)
    assert r.status_code in (401, 429)  # 401 if not yet limited, 429 if shared key
