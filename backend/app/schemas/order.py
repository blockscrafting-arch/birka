"""Order schemas."""
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

    class Config:
        from_attributes = True


class OrderItemOut(BaseModel):
    """Order item response with product info."""

    id: int
    product_id: int
    product_name: str
    barcode: str | None
    planned_qty: int
    received_qty: int
    defect_qty: int
    packed_qty: int
