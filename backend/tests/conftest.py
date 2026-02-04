"""Test fixtures."""
import asyncio
import itertools
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.session import Session
from app.db.models.user import User
from app.db.session import get_db
from app.main import app

_telegram_id_counter = itertools.count(1)


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
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
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
    session = Session(user_id=user.id, token=token, expires_at=datetime.utcnow() + timedelta(days=1))
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
    session = Session(user_id=user.id, token=token, expires_at=datetime.utcnow() + timedelta(days=1))
    db_session.add(session)
    await db_session.commit()

    return {"X-Session-Token": token}, user


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
    session = Session(user_id=user.id, token=token, expires_at=datetime.utcnow() + timedelta(days=1))
    db_session.add(session)
    await db_session.commit()

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
    session = Session(user_id=user.id, token=token, expires_at=datetime.utcnow() + timedelta(days=1))
    db_session.add(session)
    await db_session.commit()

    return {"X-Session-Token": token}
