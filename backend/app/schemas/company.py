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
    kpp: str | None = None
    ogrn: str | None = None
    legal_address: str | None = None
    okved: str | None = None
    okved_name: str | None = None
    bank_name: str | None = None
    bank_corr_account: str | None = None


class CompanyUpdate(BaseModel):
    """Update company request."""

    name: str | None = None
    legal_form: str | None = None
    director: str | None = None
    bank_bik: str | None = None
    bank_account: str | None = None
    kpp: str | None = None
    ogrn: str | None = None
    legal_address: str | None = None
    okved: str | None = None
    okved_name: str | None = None
    bank_name: str | None = None
    bank_corr_account: str | None = None


class CompanyOut(BaseModel):
    """Company response."""

    id: int
    inn: str
    name: str
    legal_form: str | None
    director: str | None
    bank_bik: str | None
    bank_account: str | None
    kpp: str | None
    ogrn: str | None
    legal_address: str | None
    okved: str | None
    okved_name: str | None
    bank_name: str | None
    bank_corr_account: str | None

    class Config:
        from_attributes = True


class CompanyList(BaseModel):
    """Paginated company list."""

    items: list[CompanyOut]
    total: int
    page: int
    limit: int


def _mask_key(value: str | None) -> str | None:
    """Return masked key for API response (e.g. ****abc1)."""
    if not value or len(value) < 4:
        return "****" if value else None
    return "****" + value[-4:]


class CompanyAPIKeysOut(BaseModel):
    """API keys response (masked)."""

    company_id: int
    wb_api_key: str | None  # masked
    ozon_client_id: str | None  # can show last 4 or mask
    ozon_api_key: str | None  # masked

    class Config:
        from_attributes = True


class CompanyAPIKeysUpdate(BaseModel):
    """Update company API keys (WB/Ozon)."""

    wb_api_key: str | None = None
    ozon_client_id: str | None = None
    ozon_api_key: str | None = None
