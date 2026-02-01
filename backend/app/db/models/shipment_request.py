"""Shipment request model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ShipmentRequest(Base):
    """Shipment request from client."""

    __tablename__ = "shipment_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    destination_type: Mapped[str] = mapped_column(String(32))
    destination_comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="Создано")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="shipment_requests")
