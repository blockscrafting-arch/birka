"""API dependencies."""
from datetime import datetime, timedelta
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import validate_telegram_init_data
from app.db.models.session import Session
from app.db.models.user import User
from app.db.session import get_db
from app.services.telegram import parse_init_data_user


def _role_for_telegram_id(telegram_id: int) -> str:
    """Return role for telegram_id: admin if in ADMIN_TELEGRAM_IDS else client."""
    return "admin" if telegram_id in settings.admin_telegram_ids else "client"


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
) -> User:
    """Resolve current user from Telegram initData header."""
    if x_session_token:
        result = await db.execute(
            select(Session).where(Session.token == x_session_token, Session.expires_at > datetime.utcnow())
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия истекла")
        user_result = await db.execute(select(User).where(User.id == session.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")
        return user

    if not x_telegram_init_data or not validate_telegram_init_data(x_telegram_init_data):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")

    user_data = parse_init_data_user(x_telegram_init_data)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")

    telegram_id = int(user_data["id"])
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            telegram_id=telegram_id,
            telegram_username=user_data.get("username"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            role=_role_for_telegram_id(telegram_id),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


def require_roles(*roles: str):
    """Dependency for role-based access control."""

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён")
        return current_user

    return checker
