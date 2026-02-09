"""Fernet encryption for sensitive data (e.g. API keys)."""
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _get_fernet() -> Fernet:
    """Return Fernet instance; raise if ENCRYPTION_KEY is not set."""
    key = (settings.ENCRYPTION_KEY or "").strip()
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is not configured")
    return Fernet(key.encode("utf-8"))


def encrypt(plaintext: str) -> str:
    """Encrypt plaintext and return base64 url-safe token."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    """Decrypt token and return plaintext. Raises on invalid token."""
    f = _get_fernet()
    try:
        return f.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Decryption failed") from exc
