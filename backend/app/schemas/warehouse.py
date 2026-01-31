"""Warehouse schemas."""
from pydantic import BaseModel


class ReceivingItem(BaseModel):
    """Receiving item."""

    order_item_id: int
    received_qty: int
    defect_qty: int = 0


class ReceivingComplete(BaseModel):
    """Complete receiving."""

    order_id: int
    items: list[ReceivingItem]


class PackingRecordCreate(BaseModel):
    """Create packing record."""

    order_id: int
    product_id: int
    employee_code: str
    pallet_number: int | None = None
    box_number: int | None = None
    quantity: int
    warehouse: str | None = None
    box_barcode: str | None = None
    materials_used: str | None = None
    time_spent_minutes: int | None = None


class BarcodeValidateRequest(BaseModel):
    """Validate barcode request."""

    barcode: str
