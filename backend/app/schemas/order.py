"""Order schemas."""
from datetime import datetime

from pydantic import BaseModel


class OrderItemCreate(BaseModel):
    """Create order item."""

    product_id: int
    planned_qty: int


class OrderCreate(BaseModel):
    """Create order request."""

    company_id: int
    destination: str | None = None
    items: list[OrderItemCreate]


class OrderStatusUpdate(BaseModel):
    """Update order status."""

    status: str


class OrderOut(BaseModel):
    """Order response."""

    id: int
    company_id: int
    order_number: str
    status: str
    destination: str | None
    planned_qty: int
    received_qty: int
    packed_qty: int
    photo_count: int = 0

    class Config:
        from_attributes = True


class OrderList(BaseModel):
    """Paginated order list."""

    items: list[OrderOut]
    total: int
    page: int
    limit: int


class OrderItemOut(BaseModel):
    """Order item response with product info."""

    id: int
    product_id: int
    product_name: str
    barcode: str | None
    brand: str | None
    size: str | None
    color: str | None
    wb_article: str | None
    wb_url: str | None
    packing_instructions: str | None
    supplier_name: str | None
    planned_qty: int
    received_qty: int
    defect_qty: int
    packed_qty: int
    adjustment_qty: int
    adjustment_note: str | None


class OrderPhotoOut(BaseModel):
    """Order photo response."""

    id: int
    s3_key: str
    url: str
    photo_type: str | None
    product_id: int | None
    created_at: datetime