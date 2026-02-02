"""OpenAI integration."""
from sqlalchemy.ext.asyncio import AsyncSession

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.rag import build_rag_context, build_rag_context_async


class OpenAIService:
    """OpenAI chat wrapper."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat(self, message: str, db: AsyncSession | None = None) -> str:
        """Send a chat message and return response. Uses RAG when db is provided."""
        if db:
            prompt = await build_rag_context_async(db, message) or message
        else:
            prompt = build_rag_context(message) or message
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""
