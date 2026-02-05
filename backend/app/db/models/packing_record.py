"""Packing record model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PackingRecord(Base):
    """Packaging record for warehouse."""

    __tablename__ = "packing_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey("order_items.id"), index=True, nullable=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("warehouse_employees.id"), index=True)
    pallet_number: Mapped[int | None] = mapped_column(Integer)
    box_number: Mapped[int | None] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    warehouse: Mapped[str | None] = mapped_column(String(128))
    box_barcode: Mapped[str | None] = mapped_column(String(128))
    materials_used: Mapped[str | None] = mapped_column(Text)
    time_spent_minutes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="packing_records")
    product = relationship("Product")
    employee = relationship("WarehouseEmployee")
