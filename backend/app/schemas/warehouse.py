"""Warehouse schemas."""
from datetime import datetime
from typing import Literal

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


class BarcodeValidateProduct(BaseModel):
    """Product in barcode validate response."""

    id: int
    name: str
    brand: str | None
    size: str | None
    color: str | None
    wb_article: str | None
    barcode: str | None


class BarcodeValidateBox(BaseModel):
    """FBO box in barcode validate response."""

    id: int
    box_number: int
    supply_id: int
    external_box_id: str | None
    external_barcode: str | None


class BarcodeValidateResponse(BaseModel):
    """Validate barcode response (product or FBO box)."""

    valid: bool
    message: str
    type: Literal["product", "box"] = "product"
    product: BarcodeValidateProduct | None = None
    box: BarcodeValidateBox | None = None


class BarcodeValidateInOrderRequest(BaseModel):
    """Validate barcode in order context request."""

    barcode: str = Field(..., max_length=128)
    order_id: int


class BarcodeValidateInOrderOrderItem(BaseModel):
    """Order item in validate-in-order response."""

    id: int
    product_id: int
    product_name: str
    planned_qty: int
    received_qty: int
    packed_qty: int
    defect_qty: int


class BarcodeValidateInOrderResponse(BaseModel):
    """Validate barcode in order response."""

    found: bool
    message: str
    order_item: BarcodeValidateInOrderOrderItem | None = None
    remaining_to_receive: int = 0
    remaining_to_pack: int = 0
