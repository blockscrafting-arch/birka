"""Order counter model."""
from datetime import date

from sqlalchemy import Date, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrderCounter(Base):
    """Daily order counter for unique order numbers."""

    __tablename__ = "order_counters"

    id: Mapped[int] = mapped_column(primary_key=True)
    counter_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    value: Mapped[int] = mapped_column(Integer, default=0)
