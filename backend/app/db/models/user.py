"""User model."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """Telegram user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32), default="client")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    companies = relationship("Company", back_populates="user")
    warehouse_profile = relationship("WarehouseEmployee", back_populates="user", uselist=False)
    chat_messages = relationship("ChatMessage", back_populates="user")