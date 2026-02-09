"""FBO supply schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class FBOSupplyItemCreate(BaseModel):
    """Item in a box."""

    product_id: int
    quantity: int = Field(ge=1)
    barcode: str | None = None


class FBOSupplyBoxCreate(BaseModel):
    """Box in a supply."""

    box_number: int = Field(ge=1)
    items: list[FBOSupplyItemCreate] = Field(min_length=1)


class FBOSupplyCreate(BaseModel):
    """Create FBO supply (draft)."""

    company_id: int
    marketplace: str = Field(pattern="^(wb|ozon)$")
    warehouse_name: str | None = None
    boxes: list[FBOSupplyBoxCreate] = Field(min_length=1)


class FBOSupplyItemOut(BaseModel):
    """Item in response."""

    id: int
    box_id: int
    product_id: int
    quantity: int
    barcode: str | None

    class Config:
        from_attributes = True


class FBOSupplyBoxOut(BaseModel):
    """Box in response."""

    id: int
    supply_id: int
    box_number: int
    barcode: str | None
    sticker_s3_key: str | None
    external_box_id: str | None = None
    items: list[FBOSupplyItemOut] = []

    class Config:
        from_attributes = True


class FBOSupplyOut(BaseModel):
    """FBO supply response."""

    id: int
    company_id: int
    marketplace: str
    external_supply_id: str | None
    warehouse_name: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    boxes: list[FBOSupplyBoxOut] = []

    class Config:
        from_attributes = True


class FBOSupplyStatusUpdate(BaseModel):
    """Update supply status."""

    status: str = Field(pattern="^(draft|active|delivering|accepted|cancelled)$")


class FBOBarcodeImport(BaseModel):
    """Import barcodes for boxes: box_number -> barcode."""

    barcodes: dict[int, str] = Field(description="box_number -> barcode")
