"""Product models."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Product(Base):
    """Product details."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(256))
    brand: Mapped[str | None] = mapped_column(String(128))
    size: Mapped[str | None] = mapped_column(String(64))
    color: Mapped[str | None] = mapped_column(String(64))
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    wb_article: Mapped[str | None] = mapped_column(String(64))
    wb_url: Mapped[str | None] = mapped_column(String(512))
    packing_instructions: Mapped[str | None] = mapped_column(Text)
    supplier_name: Mapped[str | None] = mapped_column(String(256))
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    defect_quantity: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="products")
    photos = relationship("ProductPhoto", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")


class ProductPhoto(Base):
    """Product photo stored in S3."""

    __tablename__ = "product_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    s3_key: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="photos")
