"""Company API keys for WB/Ozon marketplace integration."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CompanyAPIKeys(Base):
    """API keys per company for Wildberries and Ozon (stored per company)."""

    __tablename__ = "company_api_keys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), unique=True, index=True
    )
    wb_api_key: Mapped[str | None] = mapped_column(String(512))
    ozon_client_id: Mapped[str | None] = mapped_column(String(128))
    ozon_api_key: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    company = relationship("Company", back_populates="api_keys")
