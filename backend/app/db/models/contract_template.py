"""Contract template model."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ContractTemplate(Base):
    """
    Contract template for PDF generation.
    Supports HTML (legacy) or file-based (DOCX/PDF) templates.
    For file templates: file_key is S3 key of uploaded file; docx_key is set when
    original was PDF (converted DOCX stored in S3). html_content is optional for file templates.
    """

    __tablename__ = "contract_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    html_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    # File-based template (DOCX or PDF)
    file_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'docx' | 'pdf'
    docx_key: Mapped[str | None] = mapped_column(String(512), nullable=True)  # converted DOCX when original is PDF