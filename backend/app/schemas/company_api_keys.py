"""Company API keys schemas."""

from pydantic import BaseModel, Field


class CompanyAPIKeysSet(BaseModel):
    """Payload to set API keys (plain text; will be encrypted on server)."""

    wb_api_key: str | None = Field(None, max_length=512)
    ozon_client_id: str | None = Field(None, max_length=128)
    ozon_api_key: str | None = Field(None, max_length=512)


class CompanyAPIKeysOut(BaseModel):
    """Response with masked key presence (no raw values)."""

    has_wb: bool = False
    has_ozon_client_id: bool = False
    has_ozon_api_key: bool = False

    class Config:
        from_attributes = True
