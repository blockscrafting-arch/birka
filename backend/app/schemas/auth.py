"""Auth schemas."""
from pydantic import BaseModel


class TelegramAuthRequest(BaseModel):
    """Telegram WebApp init data."""

    init_data: str


class TelegramAuthResponse(BaseModel):
    """Auth response."""

    user_id: int
    role: str
    session_token: str
    expires_at: str


class UserMe(BaseModel):
    """Current user info."""

    id: int
    telegram_id: int
    telegram_username: str | None
    first_name: str | None
    last_name: str | None
    role: str

    model_config = {"from_attributes": True}
