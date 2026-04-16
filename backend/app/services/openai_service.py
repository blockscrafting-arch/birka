"""OpenAI/OpenRouter integration with optional function calling."""
import json
from typing import Any

from app.core.config import settings
from app.services import ai_tools
from app.services.llm_provider import get_default_model, get_llm_client


class OpenAIService:
    """LLM chat wrapper (OpenAI or OpenRouter). Supports tools for DB data access."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> None:
        self.provider = provider or settings.AI_PROVIDER
        self.model = model or get_default_model(self.provider)
        self.temperature = temperature
        api_key = settings.OPENROUTER_API_KEY if self.provider == "openrouter" else settings.OPENAI_API_KEY
        self.client = get_llm_client(self.provider, api_key)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        db=None,
        user=None,
        company_id: int | None = None,
    ) -> str:
        """
        Send chat messages to LLM and return assistant reply.
        If db, user, company_id are provided, tools are enabled and tool_calls are executed.
        messages: list of {"role": "user"|"assistant"|"tool", "content": "...", ...} in order.
        """
        if not messages:
            return ""
        use_tools = db is not None and user is not None
        if use_tools:
            return await self._chat_with_tools(messages, db, user, company_id)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

    async def _chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        db,
        user,
        company_id: int | None,
    ) -> str:
        """Call LLM with tools; execute tool_calls and loop until final answer."""
        max_rounds = 10
        for _ in range(max_rounds):
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=ai_tools.TOOLS,
                tool_choice="auto",
                temperature=self.temperature,
            )
            msg = response.choices[0].message
            if not msg.tool_calls:
                return msg.content or ""

            # Append assistant message with tool_calls
            assistant_msg = {"role": "assistant", "content": msg.content or None, "tool_calls": []}
            for tc in msg.tool_calls:
                assistant_msg["tool_calls"].append(
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                )
            messages.append(assistant_msg)

            # Execute each tool and append tool results
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = await ai_tools.execute_tool(name, args, db, user, company_id)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        return "Не удалось получить ответ после нескольких запросов к данным."
