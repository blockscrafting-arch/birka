"""Admin schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class RoleUpdate(BaseModel):
    """Update user role."""

    role: str


class AdminUserOut(BaseModel):
    """Admin user response."""

    id: int
    telegram_id: int
    telegram_username: str | None
    first_name: str | None
    last_name: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AISettingsOut(BaseModel):
    """AI settings response."""

    provider: str
    model: str
    temperature: float

    model_config = {"from_attributes": True}


class AISettingsUpdate(BaseModel):
    """AI settings update."""

    provider: str | None = Field(None, min_length=1, max_length=32)
    model: str | None = Field(None, min_length=1, max_length=128)
    temperature: float | None = None
