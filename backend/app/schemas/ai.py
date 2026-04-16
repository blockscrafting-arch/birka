"""AI schemas."""
from pydantic import BaseModel, Field, field_validator


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

    message: str = Field(..., min_length=1, max_length=8000)
    company_id: int | None = None
    history: list[ChatMessage] = []


class AIChatResponse(BaseModel):
    """AI chat response."""

    answer: str


class ChatMessageOut(BaseModel):
    """Single message for history API."""

    role: str
    text: str


class AIChatHistoryOut(BaseModel):
    """AI chat history (last N messages)."""

    messages: list[ChatMessageOut]
