"""Encryption helpers for sensitive values (e.g. API keys). Uses Fernet (AES)."""
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.logging import logger


def _get_fernet(secret: str) -> Optional[Fernet]:
    """Build Fernet from ENCRYPTION_KEY (base64 url-safe, 44 chars)."""
    if not secret or not secret.strip():
        return None
    key = secret.strip()
    try:
        return Fernet(key.encode())
    except Exception as e:
        logger.warning("crypto_fernet_init_failed", error=str(e))
        return None


def encrypt_value(plain: Optional[str], secret: str) -> Optional[str]:
    """
    Encrypt string for storage. Returns None if plain is None or encryption unavailable.
    """
    if plain is None or (isinstance(plain, str) and not plain.strip()):
        return None
    f = _get_fernet(secret)
    if not f:
        return plain
    try:
        return f.encrypt(plain.encode()).decode()
    except Exception as e:
        logger.warning("crypto_encrypt_failed", error=str(e))
        return plain


def decrypt_value(cipher: Optional[str], secret: str) -> Optional[str]:
    """
    Decrypt stored value. If decryption fails (e.g. legacy plaintext), return as-is.
    """
    if cipher is None or (isinstance(cipher, str) and not cipher.strip()):
        return None
    f = _get_fernet(secret)
    if not f:
        return cipher
    try:
        return f.decrypt(cipher.encode()).decode()
    except InvalidToken:
        return cipher
    except Exception as e:
        logger.warning("crypto_decrypt_failed", error=str(e))
        return cipher
