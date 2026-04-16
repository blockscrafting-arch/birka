"""Destination model (address/shipment lookup)."""
from datetime import datetime

from sqlalchemy import DateTime, Boolean, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Destination(Base):
    """Destination (address) for orders, managed in admin."""

    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
