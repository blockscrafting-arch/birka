"""Security helpers for Telegram WebApp."""
import hashlib
import hmac
import time
from urllib.parse import parse_qsl

from app.core.config import settings


def validate_telegram_init_data(init_data: str, max_age_seconds: int = 300) -> bool:
    """Validate Telegram WebApp initData by HMAC-SHA256 and auth_date (replay protection)."""
    if not init_data:
        return False

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    auth_date = parsed.get("auth_date")
    if auth_date:
        try:
            if int(auth_date) < time.time() - max_age_seconds:
                return False
        except (ValueError, TypeError):
            return False

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.TELEGRAM_BOT_TOKEN.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parse_qsl(init_data, keep_blank_values=True))
        if k != "hash"
    )
    provided_hash = parsed.get("hash", "")

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(calculated_hash, provided_hash)
