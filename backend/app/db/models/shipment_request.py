"""Shipment request model."""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ShipmentRequest(Base):
    """Shipment request from client."""

    __tablename__ = "shipment_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), index=True)
    fbo_supply_id: Mapped[int | None] = mapped_column(ForeignKey("fbo_supplies.id"), index=True)
    destination_type: Mapped[str] = mapped_column(String(32))
    destination_comment: Mapped[str | None] = mapped_column(Text)
    warehouse_name: Mapped[str | None] = mapped_column(String(128))
    delivery_date: Mapped[date | None] = mapped_column(Date)
    supply_barcode_key: Mapped[str | None] = mapped_column(String(512))
    box_barcodes_key: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="Создано")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="shipment_requests")
    order = relationship("Order", back_populates="shipment_requests")
    fbo_supply = relationship("FBOSupply", back_populates="shipment_requests")
