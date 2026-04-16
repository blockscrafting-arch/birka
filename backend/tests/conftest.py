"""Test fixtures."""

import asyncio
import itertools
import sys
import types
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Platform mock for weasyprint (requires GTK — not available on Windows/CI-lite)
# ---------------------------------------------------------------------------
def _mock_weasyprint():
    """Mock weasyprint and its C-level dependencies so tests run without GTK."""
    if "weasyprint" not in sys.modules:
        wp = types.ModuleType("weasyprint")
        mock_html = MagicMock()
        mock_html.return_value.write_pdf.return_value = b"%PDF-1.4 mock\n" + b"0" * 2000 + b"\n%%EOF"
        wp.HTML = mock_html
        wp.CSS = MagicMock()
        sys.modules["weasyprint"] = wp
        # Mock gobject / pango sub-dependencies that weasyprint's ffi imports
        for _name in [
            "weasyprint.text",
            "weasyprint.text.ffi",
            "weasyprint.css",
            "weasyprint.css.computed_values",
            "weasyprint.css.counters",
            "weasyprint.css.media_queries",
        ]:
            sys.modules[_name] = types.ModuleType(_name)


_mock_weasyprint()
# ---------------------------------------------------------------------------

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.order_counter import OrderCounter
from app.db.models.session import Session
from app.db.models.user import User
from app.db.session import get_db
from app.main import app

_telegram_id_counter = itertools.count(1)
_inn_counter = itertools.count(1100000000)  # уникальные ИНН для тестов (избегаем UNIQUE constraint)


@pytest.fixture
def unique_inn():
    """Уникальный ИНН для каждого теста (общая in-memory БД в тестах)."""
    return str(next(_inn_counter))


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop


@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def db_session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture()
async def db_session_expire_on_commit(engine):
    """Session with expire_on_commit=True (production-like) for testing complete_order."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=True)
    async with async_session() as session:
        yield session


@pytest.fixture()
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
async def auth_headers(db_session):
    telegram_id = next(_telegram_id_counter)
    user = User(
        telegram_id=telegram_id,
        telegram_username=f"user-{telegram_id}",
        first_name="Test",
        role="client",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = f"test-token-{telegram_id}"
    session = Session(
        user_id=user.id, token=token, expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None)
    )
    db_session.add(session)
    await db_session.commit()

    return {"X-Session-Token": token}


@pytest.fixture()
async def auth_headers_and_user(db_session):
    """Same as auth_headers but also yields the user (for tests that create companies)."""
    telegram_id = next(_telegram_id_counter)
    user = User(
        telegram_id=telegram_id,
        telegram_username=f"user-{telegram_id}",
        first_name="Test",
        role="client",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = f"test-token-{telegram_id}"
    session = Session(
        user_id=user.id, token=token, expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None)
    )
    db_session.add(session)
    await db_session.commit()

    return {"X-Session-Token": token}, user


@pytest.fixture()
async def second_auth_headers_and_user(db_session):
    """Second user for IDOR tests — separate telegram_id."""
    telegram_id = next(_telegram_id_counter)
    user = User(
        telegram_id=telegram_id,
        telegram_username=f"user2-{telegram_id}",
        first_name="Test2",
        role="client",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = f"test2-token-{telegram_id}"
    session = Session(
        user_id=user.id, token=token, expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None)
    )
    db_session.add(session)
    await db_session.commit()

    return {"X-Session-Token": token}, user


@pytest.fixture()
def mock_notification():
    """Mock Telegram notification to avoid real HTTP calls in tests."""
    with patch("app.api.v1.routes.warehouse.send_notification", new_callable=AsyncMock) as m:
        m.return_value = True
        yield m


@pytest.fixture()
async def order_with_receiving(
    client, auth_headers_and_user, warehouse_headers, db_session, unique_inn, mock_notification
):
    """Ready order after receiving — for packing tests.

    Returns dict: {company_id, product_id, order_id, order_item_id, headers, w_headers}
    Uses OrderCounter workaround: pre-inserts counter row since SQLite lacks ON CONFLICT support.
    """
    from sqlalchemy import select as sa_select

    headers, _user = auth_headers_and_user

    # OrderCounter workaround for SQLite (no ON CONFLICT support)
    today = date.today()
    existing = await db_session.execute(sa_select(OrderCounter).where(OrderCounter.counter_date == today))
    if not existing.scalar_one_or_none():
        db_session.add(OrderCounter(counter_date=today, value=0))
        await db_session.commit()

    company_resp = await client.post("/api/v1/companies", json={"inn": unique_inn}, headers=headers)
    assert company_resp.status_code in (200, 201)
    company_id = company_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products",
        json={"company_id": company_id, "name": "Тест упаковки", "stock_quantity": 0},
        headers=headers,
    )
    assert product_resp.status_code in (200, 201)
    product_id = product_resp.json()["id"]

    order_resp = await client.post(
        "/api/v1/orders",
        json={"company_id": company_id, "items": [{"product_id": product_id, "planned_qty": 10}]},
        headers=headers,
    )
    assert order_resp.status_code == 200, order_resp.text
    order_id = order_resp.json()["id"]

    items_resp = await client.get(f"/api/v1/orders/{order_id}/items", headers=headers)
    assert items_resp.status_code == 200
    order_item_id = items_resp.json()[0]["id"]

    recv_resp = await client.post(
        "/api/v1/warehouse/receiving/complete",
        json={"order_id": order_id, "items": [{"order_item_id": order_item_id, "received_qty": 10, "defect_qty": 0}]},
        headers=warehouse_headers,
    )
    assert recv_resp.status_code == 200, recv_resp.text

    return {
        "company_id": company_id,
        "product_id": product_id,
        "order_id": order_id,
        "order_item_id": order_item_id,
        "headers": headers,
        "w_headers": warehouse_headers,
    }


@pytest.fixture()
async def warehouse_headers(db_session):
    telegram_id = next(_telegram_id_counter)
    user = User(
        telegram_id=telegram_id,
        telegram_username=f"worker-{telegram_id}",
        first_name="Worker",
        role="warehouse",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = f"warehouse-token-{telegram_id}"
    session = Session(
        user_id=user.id, token=token, expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None)
    )
    db_session.add(session)
    await db_session.commit()

    return {"X-Session-Token": token}


@pytest.fixture()
async def warehouse_headers_and_user(db_session):
    """Warehouse headers and user (e.g. to assert FBO send goes to current_user)."""
    telegram_id = next(_telegram_id_counter)
    user = User(
        telegram_id=telegram_id,
        telegram_username=f"worker-{telegram_id}",
        first_name="Worker",
        role="warehouse",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token = f"warehouse-token-{telegram_id}"
    session = Session(
        user_id=user.id, token=token, expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None)
    )
    db_session.add(session)
    await db_session.commit()
    return {"X-Session-Token": token}, user


@pytest.fixture()
async def client_expire_on_commit(db_session_expire_on_commit):
    """Client using session with expire_on_commit=True (production-like)."""

    async def override_get_db():
        yield db_session_expire_on_commit

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
async def auth_headers_expire_on_commit(db_session_expire_on_commit):
    """Auth headers for client user, using expire_on_commit session."""
    telegram_id = next(_telegram_id_counter)
    user = User(
        telegram_id=telegram_id,
        telegram_username=f"user-{telegram_id}",
        first_name="Test",
        role="client",
    )
    db_session_expire_on_commit.add(user)
    await db_session_expire_on_commit.commit()
    await db_session_expire_on_commit.refresh(user)

    token = f"test-token-{telegram_id}"
    session = Session(
        user_id=user.id, token=token, expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None)
    )
    db_session_expire_on_commit.add(session)
    await db_session_expire_on_commit.commit()

    return {"X-Session-Token": token}


@pytest.fixture()
async def warehouse_headers_expire_on_commit(db_session_expire_on_commit):
    """Warehouse headers using expire_on_commit session."""
    telegram_id = next(_telegram_id_counter)
    user = User(
        telegram_id=telegram_id,
        telegram_username=f"worker-{telegram_id}",
        first_name="Worker",
        role="warehouse",
    )
    db_session_expire_on_commit.add(user)
    await db_session_expire_on_commit.commit()
    await db_session_expire_on_commit.refresh(user)

    token = f"warehouse-token-{telegram_id}"
    session = Session(
        user_id=user.id, token=token, expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None)
    )
    db_session_expire_on_commit.add(session)
    await db_session_expire_on_commit.commit()

    return {"X-Session-Token": token}


@pytest.fixture()
async def admin_headers(db_session):
    telegram_id = next(_telegram_id_counter)
    user = User(
        telegram_id=telegram_id,
        telegram_username=f"admin-{telegram_id}",
        first_name="Admin",
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = f"admin-token-{telegram_id}"
    session = Session(
        user_id=user.id, token=token, expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None)
    )
    db_session.add(session)
    await db_session.commit()

    return {"X-Session-Token": token}
