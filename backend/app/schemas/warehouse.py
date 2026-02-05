"""Warehouse schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class ReceivingItem(BaseModel):
    """Receiving item."""

    order_item_id: int
    received_qty: int
    defect_qty: int = 0
    adjustment_qty: int = 0
    adjustment_note: str | None = None


class ReceivingComplete(BaseModel):
    """Complete receiving."""

    order_id: int
    items: list[ReceivingItem]


class PackingRecordCreate(BaseModel):
    """Create packing record."""

    order_id: int
    order_item_id: int
    product_id: int
    employee_code: str
    pallet_number: int | None = None
    box_number: int | None = None
    quantity: int = Field(..., gt=0, description="Количество упакованных шт.")
    warehouse: str | None = None
    box_barcode: str | None = None
    materials_used: str | None = None
    time_spent_minutes: int | None = None


class PackingRecordOut(BaseModel):
    """Packing record for client (order detail)."""

    id: int
    product_id: int
    product_name: str
    pallet_number: int | None
    box_number: int | None
    quantity: int
    warehouse: str | None
    box_barcode: str | None
    materials_used: str | None
    time_spent_minutes: int | None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class BarcodeValidateRequest(BaseModel):
    """Validate barcode request."""

    barcode: str
