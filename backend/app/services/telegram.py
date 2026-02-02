"""Telegram helpers."""
import json
from urllib.parse import parse_qsl

import httpx

from app.core.config import settings


async def send_notification(chat_id: int, text: str) -> bool:
    """Send a text message to Telegram chat. Returns True on success."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json={"chat_id": chat_id, "text": text}, timeout=10.0)
            return resp.status_code == 200
    except Exception:
        return False


def parse_init_data_user(init_data: str) -> dict | None:
    """Extract user payload from init_data."""
    data = dict(parse_qsl(init_data))
    user_raw = data.get("user")
    if not user_raw:
        return None
    try:
        return json.loads(user_raw)
    except json.JSONDecodeError:
        return None
