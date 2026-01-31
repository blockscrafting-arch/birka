"""Telegram helpers."""
import json
from urllib.parse import parse_qsl


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
