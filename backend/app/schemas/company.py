"""Company schemas."""
from pydantic import BaseModel


class CompanyCreate(BaseModel):
    """Create company request."""

    inn: str
    name: str | None = None
    legal_form: str | None = None
    director: str | None = None
    bank_bik: str | None = None
    bank_account: str | None = None


class CompanyUpdate(BaseModel):
    """Update company request."""

    name: str | None = None
    legal_form: str | None = None
    director: str | None = None
    bank_bik: str | None = None
    bank_account: str | None = None


class CompanyOut(BaseModel):
    """Company response."""

    id: int
    inn: str
    name: str
    legal_form: str | None
    director: str | None
    bank_bik: str | None
    bank_account: str | None

    class Config:
        from_attributes = True
