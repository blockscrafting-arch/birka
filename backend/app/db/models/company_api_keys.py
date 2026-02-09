"""Company API keys for WB/Ozon (stored encrypted)."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CompanyAPIKeys(Base):
    """Encrypted API keys for marketplace integrations (WB, Ozon)."""

    __tablename__ = "company_api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), unique=True, index=True)
    wb_api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    ozon_client_id_encrypted: Mapped[str | None] = mapped_column(Text)
    ozon_api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="api_keys")
