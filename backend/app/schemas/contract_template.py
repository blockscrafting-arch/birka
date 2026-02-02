"""Contract template schemas."""
from datetime import datetime

from pydantic import BaseModel


class ContractTemplateOut(BaseModel):
    """Contract template response."""

    id: int
    name: str
    html_content: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContractTemplateCreate(BaseModel):
    """Create contract template request."""

    name: str
    html_content: str
    is_default: bool = False


class ContractTemplateUpdate(BaseModel):
    """Update contract template request."""

    name: str | None = None
    html_content: str | None = None
    is_default: bool | None = None
