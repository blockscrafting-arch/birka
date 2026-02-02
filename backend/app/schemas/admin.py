"""Admin schemas."""
from datetime import datetime

from pydantic import BaseModel


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
