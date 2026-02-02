"""Company model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Company(Base):
    """Client company details."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    inn: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    legal_form: Mapped[str | None] = mapped_column(String(32))
    director: Mapped[str | None] = mapped_column(String(128))
    bank_bik: Mapped[str | None] = mapped_column(String(16))
    bank_account: Mapped[str | None] = mapped_column(String(32))
    kpp: Mapped[str | None] = mapped_column(String(16))
    ogrn: Mapped[str | None] = mapped_column(String(20))
    legal_address: Mapped[str | None] = mapped_column(String(512))
    okved: Mapped[str | None] = mapped_column(String(16))
    okved_name: Mapped[str | None] = mapped_column(String(256))
    bank_name: Mapped[str | None] = mapped_column(String(256))
    bank_corr_account: Mapped[str | None] = mapped_column(String(32))
    contract_data: Mapped[dict | None] = mapped_column(JSONB().with_variant(JSON, "sqlite"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="companies")
    products = relationship("Product", back_populates="company")
    orders = relationship("Order", back_populates="company")
    shipment_requests = relationship("ShipmentRequest", back_populates="company")