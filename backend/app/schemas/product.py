"""Product schemas."""
from pydantic import BaseModel


class ProductCreate(BaseModel):
    """Create product request."""

    company_id: int
    name: str
    brand: str | None = None
    size: str | None = None
    color: str | None = None
    barcode: str | None = None
    wb_article: str | None = None
    wb_url: str | None = None
    packing_instructions: str | None = None
    supplier_name: str | None = None


class ProductUpdate(BaseModel):
    """Update product request."""

    name: str | None = None
    brand: str | None = None
    size: str | None = None
    color: str | None = None
    barcode: str | None = None
    wb_article: str | None = None
    wb_url: str | None = None
    packing_instructions: str | None = None
    supplier_name: str | None = None


class ProductOut(BaseModel):
    """Product response."""

    id: int
    company_id: int
    name: str
    brand: str | None
    size: str | None
    color: str | None
    barcode: str | None
    wb_article: str | None
    wb_url: str | None
    packing_instructions: str | None
    supplier_name: str | None
    stock_quantity: int
    defect_quantity: int

    class Config:
        from_attributes = True


class ProductList(BaseModel):
    """Paginated product list."""

    items: list[ProductOut]
    total: int
    page: int
    limit: int


class ImportSkipped(BaseModel):
    """Skipped row in product import (e.g. barcode belongs to another company)."""

    barcode: str
    name: str
    reason: str


class ImportResult(BaseModel):
    """Product import result with duplicate report."""

    imported: int
    updated: int
    skipped: list[ImportSkipped] = []
