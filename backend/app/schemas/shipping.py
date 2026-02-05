"""Shipment request schemas."""
from datetime import date, datetime

from pydantic import BaseModel


class ShipmentRequestCreate(BaseModel):
    """Create shipment request."""

    company_id: int
    order_id: int | None = None
    destination_type: str
    destination_comment: str | None = None
    warehouse_name: str | None = None
    delivery_date: date | None = None


class ShipmentRequestOut(BaseModel):
    """Shipment request response."""

    id: int
    company_id: int
    order_id: int | None
    order_number: str | None
    fbo_supply_id: int | None = None
    destination_type: str
    destination_comment: str | None
    warehouse_name: str | None
    delivery_date: date | None
    supply_barcode_url: str | None
    box_barcodes_url: str | None
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
