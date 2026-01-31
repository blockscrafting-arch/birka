"""AI schemas."""
from pydantic import BaseModel


class AIChatRequest(BaseModel):
    """AI chat request."""

    message: str
    company_id: int | None = None


class AIChatResponse(BaseModel):
    """AI chat response."""

    answer: str
