"""OpenAI integration."""
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.rag import build_rag_context
from app.core.logging import logger


class OpenAIService:
    """OpenAI chat wrapper."""

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat(self, message: str) -> str:
        """Send a chat message and return response."""
        prompt = build_rag_context(message) or message
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("openai_chat_failed", error=str(exc))
            raise RuntimeError("AI сервис временно недоступен") from exc
