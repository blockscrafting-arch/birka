"""Service (pricing) schemas."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ServiceOut(BaseModel):
    """Service response."""

    id: int
    category: str
    name: str
    price: Decimal
    unit: str
    comment: str | None
    is_active: bool
    sort_order: int

    model_config = {"from_attributes": True}


class ServiceCreate(BaseModel):
    """Create service request."""

    category: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=256)
    price: Decimal = Field(..., ge=0)
    unit: str = Field(default="шт", max_length=50)
    comment: str | None = None
    is_active: bool = True
    sort_order: int = 0


class ServiceUpdate(BaseModel):
    """Update service request. Pass empty string for comment to clear it."""

    category: str | None = Field(None, min_length=1, max_length=100)
    name: str | None = Field(None, min_length=1, max_length=256)
    price: Decimal | None = Field(None, ge=0)
    unit: str | None = Field(None, max_length=50)
    comment: str | None = Field(None, description="Pass empty string to clear")
    is_active: bool | None = None
    sort_order: int | None = None


class CalculateItem(BaseModel):
    """Single item for cost calculation."""

    service_id: int
    quantity: float = Field(..., ge=0)


class CalculateRequest(BaseModel):
    """Request body for cost calculation."""

    items: list[CalculateItem] = Field(..., min_length=1)


class CalculateItemOut(BaseModel):
    """Line item in calculation result."""

    service_id: int
    name: str
    category: str
    price: Decimal
    unit: str
    quantity: float
    subtotal: Decimal


class CalculateResponse(BaseModel):
    """Cost calculation result."""

    items: list[CalculateItemOut]
    total: Decimal


class ServiceReorderItem(BaseModel):
    """Id and new sort_order for reorder."""

    id: int
    sort_order: int


class ServiceReorderRequest(BaseModel):
    """Request body for reorder."""

    items: list[ServiceReorderItem] = Field(..., min_length=1)


class ServicePriceHistoryOut(BaseModel):
    """Single price change record."""

    id: int
    service_id: int
    old_price: Decimal
    new_price: Decimal
    changed_at: datetime
    changed_by_user_id: int | None

    model_config = {"from_attributes": True}
