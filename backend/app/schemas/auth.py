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
