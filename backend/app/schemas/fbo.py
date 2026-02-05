"""FBO supply schemas for WB/Ozon."""
from datetime import datetime

from pydantic import BaseModel


class FBOSupplyBoxOut(BaseModel):
    """FBO supply box in response."""
    id: int
    supply_id: int
    box_number: int
    external_barcode: str | None

    class Config:
        from_attributes = True


class FBOSupplyOut(BaseModel):
    """FBO supply response."""
    id: int
    order_id: int | None
    company_id: int
    marketplace: str
    external_supply_id: str | None
    status: str
    warehouse_name: str | None
    created_at: datetime
    boxes: list[FBOSupplyBoxOut] = []

    class Config:
        from_attributes = True


class FBOSupplyCreate(BaseModel):
    """Create FBO supply draft."""
    company_id: int
    order_id: int | None = None
    marketplace: str = Field(..., pattern="^(wb|ozon)$", description="wb или ozon")


class FBOSupplyImportBarcodes(BaseModel):
    """Import box barcodes manually (max 500 items)."""
    barcodes: list[str] = Field(..., max_length=500)


class FBOSupplyList(BaseModel):
    """Paginated FBO supply list."""
    items: list[FBOSupplyOut]
    total: int
    page: int
    limit: int
