"""Auth tests — auth flow, session lifecycle, RBAC."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.db.models.session import Session
from app.db.models.user import User


async def test_logout_requires_token(client):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 400


async def test_logout_success(client, auth_headers):
    response = await client.post("/api/v1/auth/logout", headers=auth_headers)
    assert response.status_code == 200


# ── Фаза 1: расширение ────────────────────────────────────────────────────────


async def test_telegram_auth_creates_user(client, db_session):
    """POST /auth/telegram creates user + returns session_token."""
    with (
        patch("app.api.v1.routes.auth.validate_telegram_init_data", return_value=True),
        patch(
            "app.api.v1.routes.auth.parse_init_data_user",
            return_value={"id": "9000001", "first_name": "New", "username": "newuser"},
        ),
    ):
        resp = await client.post("/api/v1/auth/telegram", json={"init_data": "fake"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_token" in data
    assert data["role"] in ("client", "admin")


async def test_telegram_auth_invalid_returns_401(client):
    """Invalid initData → 401."""
    with patch("app.api.v1.routes.auth.validate_telegram_init_data", return_value=False):
        resp = await client.post("/api/v1/auth/telegram", json={"init_data": "bad"})
    assert resp.status_code == 401


async def test_telegram_auth_existing_user_reuses(client, db_session):
    """Re-auth with same telegram_id reuses user, creates new token."""
    with (
        patch("app.api.v1.routes.auth.validate_telegram_init_data", return_value=True),
        patch(
            "app.api.v1.routes.auth.parse_init_data_user",
            return_value={"id": "9000002", "first_name": "Existing"},
        ),
    ):
        r1 = await client.post("/api/v1/auth/telegram", json={"init_data": "fake"})
        r2 = await client.post("/api/v1/auth/telegram", json={"init_data": "fake"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["user_id"] == r2.json()["user_id"]
    assert r1.json()["session_token"] != r2.json()["session_token"]


async def test_telegram_auth_syncs_admin_role(client, db_session):
    """telegram_id in ADMIN_TELEGRAM_IDS → role=admin."""
    with (
        patch("app.api.v1.routes.auth.validate_telegram_init_data", return_value=True),
        patch(
            "app.api.v1.routes.auth.parse_init_data_user",
            return_value={"id": "9000003", "first_name": "AdminUser"},
        ),
        patch("app.api.v1.routes.auth.settings") as mock_settings,
    ):
        mock_settings.admin_telegram_ids = {9000003}
        mock_settings.TELEGRAM_BOT_TOKEN = "fake"
        resp = await client.post("/api/v1/auth/telegram", json={"init_data": "fake"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


async def test_expired_session_returns_401(client, db_session):
    """Session with expires_at in the past → 401."""
    from itertools import count as _count
    tid = 9900000 + next(iter(range(99999)))
    user = User(telegram_id=tid, telegram_username="expired_user", first_name="Exp", role="client")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    expired_token = "expired-test-token-xyz"
    expired_session = Session(
        user_id=user.id,
        token=expired_token,
        expires_at=(datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None),
    )
    db_session.add(expired_session)
    await db_session.commit()

    resp = await client.get("/api/v1/auth/me", headers={"X-Session-Token": expired_token})
    assert resp.status_code == 401


async def test_get_me_returns_user(client, auth_headers):
    """GET /auth/me → 200 + user data."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "role" in data


async def test_get_me_no_auth_401(client):
    """No headers → 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_require_roles_denies_client(client, auth_headers):
    """client role → warehouse endpoint → 403."""
    resp = await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={"order_id": 9999, "items": []},
        headers=auth_headers,
    )
    assert resp.status_code == 403


async def test_admin_can_access_warehouse_endpoint(client, admin_headers):
    """admin role → warehouse endpoint → not 403 (may be 4xx for missing data)."""
    resp = await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={"order_id": 9999, "items": []},
        headers=admin_headers,
    )
    assert resp.status_code != 403


async def test_logout_invalidates_session(client, auth_headers):
    """After logout, same token → 401."""
    logout = await client.post("/api/v1/auth/logout", headers=auth_headers)
    assert logout.status_code == 200

    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 401
