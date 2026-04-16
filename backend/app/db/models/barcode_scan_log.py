"""Barcode scan log: journal of every barcode validation (scanner)."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BarcodeScanLog(Base):
    """One row per barcode validate call: who, when, company/order context, result."""

    __tablename__ = "barcode_scan_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True, nullable=True)
    barcode: Mapped[str] = mapped_column(String(128))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), index=True, nullable=True)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    valid: Mapped[bool] = mapped_column(Boolean)
    result_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), index=True, nullable=True)
    fbo_supply_box_id: Mapped[int | None] = mapped_column(ForeignKey("fbo_supply_boxes.id"), index=True, nullable=True)
