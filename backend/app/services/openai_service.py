"""OpenAI integration."""
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.rag import build_rag_context


class OpenAIService:
    """OpenAI chat wrapper."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat(self, message: str) -> str:
        """Send a chat message and return response."""
        prompt = build_rag_context(message) or message
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""
