"""FBO supply models for marketplace integration (WB/Ozon)."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FBOSupply(Base):
    """FBO supply (shipment to marketplace warehouse)."""

    __tablename__ = "fbo_supplies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    marketplace: Mapped[str] = mapped_column(String(32))  # wb | ozon
    external_supply_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft | created | in_progress | completed
    warehouse_name: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="fbo_supplies")
    shipment_requests = relationship("ShipmentRequest", back_populates="fbo_supply")
    boxes = relationship("FBOSupplyBox", back_populates="supply", cascade="all, delete-orphan")


class FBOSupplyBox(Base):
    """Box (pallet/короб) in an FBO supply."""

    __tablename__ = "fbo_supply_boxes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("fbo_supplies.id"), index=True)
    box_number: Mapped[int] = mapped_column(Integer)
    external_box_id: Mapped[str | None] = mapped_column(String(128))  # WB-TRBX-xxx etc
    external_barcode: Mapped[str | None] = mapped_column(String(128))  # сканируемый ШК/QR

    supply = relationship("FBOSupply", back_populates="boxes")
    items = relationship("FBOSupplyItem", back_populates="box", cascade="all, delete-orphan")


class FBOSupplyItem(Base):
    """Item (product) in an FBO supply box."""

    __tablename__ = "fbo_supply_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    box_id: Mapped[int] = mapped_column(ForeignKey("fbo_supply_boxes.id"), index=True)
    packing_record_id: Mapped[int | None] = mapped_column(ForeignKey("packing_records.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    barcode: Mapped[str] = mapped_column(String(64))

    box = relationship("FBOSupplyBox", back_populates="items")