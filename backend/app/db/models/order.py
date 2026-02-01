"""Order models."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Order(Base):
    """Supply order."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    order_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="На приемке")
    destination: Mapped[str | None] = mapped_column(String(64))
    planned_qty: Mapped[int] = mapped_column(Integer, default=0)
    received_qty: Mapped[int] = mapped_column(Integer, default=0)
    packed_qty: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    photos = relationship("OrderPhoto", back_populates="order")
    packing_records = relationship("PackingRecord", back_populates="order")


class OrderItem(Base):
    """Order line item."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    planned_qty: Mapped[int] = mapped_column(Integer, default=0)
    received_qty: Mapped[int] = mapped_column(Integer, default=0)
    packed_qty: Mapped[int] = mapped_column(Integer, default=0)
    defect_qty: Mapped[int] = mapped_column(Integer, default=0)
    adjustment_qty: Mapped[int] = mapped_column(Integer, default=0)
    adjustment_note: Mapped[str | None] = mapped_column(String(256))

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
