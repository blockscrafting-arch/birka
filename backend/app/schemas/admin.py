"""Admin schemas."""
from pydantic import BaseModel


class RoleUpdate(BaseModel):
    """Update user role."""

    role: str
