"""Destination schemas."""
from pydantic import BaseModel


class DestinationOut(BaseModel):
    """Destination response."""

    id: int
    name: str
    is_active: bool

    model_config = {"from_attributes": True}


class DestinationCreate(BaseModel):
    """Create destination request."""

    name: str


class DestinationUpdate(BaseModel):
    """Update destination request."""

    name: str | None = None
    is_active: bool | None = None
