"""AI schemas."""
from pydantic import BaseModel, field_validator


class ChatMessage(BaseModel):
    """Single message in chat history."""

    role: str  # "user" | "assistant"
    text: str

    @field_validator("role")
    @classmethod
    def role_allowed(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError("role must be 'user' or 'assistant'")
        return v


class AIChatRequest(BaseModel):
    """AI chat request."""

    message: str
    company_id: int | None = None
    history: list[ChatMessage] = []


class AIChatResponse(BaseModel):
    """AI chat response."""

    answer: str
