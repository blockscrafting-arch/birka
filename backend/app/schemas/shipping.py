"""Shipment request schemas."""
from datetime import datetime

from pydantic import BaseModel


class ShipmentRequestCreate(BaseModel):
    """Create shipment request."""

    company_id: int
    destination_type: str
    destination_comment: str | None = None


class ShipmentRequestOut(BaseModel):
    """Shipment request response."""

    id: int
    company_id: int
    destination_type: str
    destination_comment: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ShipmentRequestStatusUpdate(BaseModel):
    """Update shipment request status."""

    status: str


class ShipmentRequestList(BaseModel):
    """Paginated shipment request list."""

    items: list[ShipmentRequestOut]
    total: int
    page: int
    limit: int
