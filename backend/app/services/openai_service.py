"""OpenAI integration."""
from openai import AsyncOpenAI

from app.core.config import settings


class OpenAIService:
    """OpenAI chat wrapper."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        """
        Send chat messages to OpenAI and return assistant reply.
        messages: list of {"role": "user"|"assistant", "content": "..."} in order.
        """
        if not messages:
            return ""
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        return response.choices[0].message.content or ""
