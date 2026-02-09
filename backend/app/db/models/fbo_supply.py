"""FBO supply models (WB/Ozon)."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FBOSupply(Base):
    """FBO supply (draft or synced with marketplace)."""

    __tablename__ = "fbo_supplies"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    marketplace: Mapped[str] = mapped_column(String(16))  # "wb" | "ozon"
    external_supply_id: Mapped[str | None] = mapped_column(String(128))
    warehouse_name: Mapped[str | None] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft | active | delivering | accepted | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="fbo_supplies")
    boxes = relationship("FBOSupplyBox", back_populates="supply", cascade="all, delete-orphan")


class FBOSupplyBox(Base):
    """Box within an FBO supply."""

    __tablename__ = "fbo_supply_boxes"

    id: Mapped[int] = mapped_column(primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("fbo_supplies.id"), index=True)
    box_number: Mapped[int] = mapped_column(Integer)
    barcode: Mapped[str | None] = mapped_column(String(128))
    sticker_s3_key: Mapped[str | None] = mapped_column(String(512))
    external_box_id: Mapped[str | None] = mapped_column(String(128))  # cargo_id in Ozon
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    supply = relationship("FBOSupply", back_populates="boxes")
    items = relationship("FBOSupplyItem", back_populates="box", cascade="all, delete-orphan")


class FBOSupplyItem(Base):
    """Item (product + qty) inside an FBO box."""

    __tablename__ = "fbo_supply_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    box_id: Mapped[int] = mapped_column(ForeignKey("fbo_supply_boxes.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    barcode: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    box = relationship("FBOSupplyBox", back_populates="items")
    product = relationship("Product")
