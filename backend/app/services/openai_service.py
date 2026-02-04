"""OpenAI integration with optional function calling."""
import json
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.services import ai_tools


class OpenAIService:
    """OpenAI chat wrapper. Supports tools for DB data access."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        db=None,
        user=None,
        company_id: int | None = None,
    ) -> str:
        """
        Send chat messages to OpenAI and return assistant reply.
        If db, user, company_id are provided, tools are enabled and tool_calls are executed.
        messages: list of {"role": "user"|"assistant"|"tool", "content": "...", ...} in order.
        """
        if not messages:
            return ""
        use_tools = db is not None and user is not None
        if use_tools:
            return await self._chat_with_tools(messages, db, user, company_id)
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        return response.choices[0].message.content or ""

    async def _chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        db,
        user,
        company_id: int | None,
    ) -> str:
        """Call OpenAI with tools; execute tool_calls and loop until final answer."""
        max_rounds = 10
        for _ in range(max_rounds):
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=ai_tools.TOOLS,
                tool_choice="auto",
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
