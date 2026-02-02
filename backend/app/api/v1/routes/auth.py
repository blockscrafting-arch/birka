"""Auth endpoints."""
from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import validate_telegram_init_data
from app.api.v1.deps import get_current_user
from app.db.models.session import Session
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import TelegramAuthRequest, TelegramAuthResponse, UserMe
from app.core.config import settings
from app.services.telegram import parse_init_data_user

router = APIRouter()


@router.post("/telegram", response_model=TelegramAuthResponse)
async def telegram_auth(
    payload: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> TelegramAuthResponse:
    """Authenticate via Telegram WebApp initData."""
    if not validate_telegram_init_data(payload.init_data):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid init data")

    user_data = parse_init_data_user(payload.init_data)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found in init data")

    telegram_id = int(user_data["id"])
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            telegram_id=telegram_id,
            telegram_username=user_data.get("username"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            role="admin" if telegram_id in settings.ADMIN_TELEGRAM_IDS else "client",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    await db.execute(delete(Session).where(Session.expires_at <= datetime.utcnow()))

    token = secrets.token_hex(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    user_id = user.id
    role = user.role
    session = Session(user_id=user_id, token=token, expires_at=expires_at)
    db.add(session)
    await db.commit()

    return TelegramAuthResponse(
        user_id=user_id,
        role=role,
        session_token=token,
        expires_at=expires_at.isoformat(),
    )


@router.post("/logout")
async def logout(
    x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke current session."""
    if not x_session_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing session token")
    await db.execute(delete(Session).where(Session.token == x_session_token))
    await db.commit()
    return {"status": "ok"}


@router.get("/me", response_model=UserMe)
async def get_me(current_user: User = Depends(get_current_user)) -> UserMe:
    """Get current user info."""
    return current_user
