"""Tests for encryption helpers (API keys storage)."""
from cryptography.fernet import Fernet

from app.core.crypto import decrypt_value, encrypt_value


def test_encrypt_decrypt_roundtrip():
    """Encrypt then decrypt returns original value."""
    key = Fernet.generate_key().decode()
    plain = "secret-api-key-123"
    cipher = encrypt_value(plain, key)
    assert cipher is not None
    assert cipher != plain
    assert decrypt_value(cipher, key) == plain


def test_encrypt_none_returns_none():
    """Encrypting None or empty string returns None."""
    key = Fernet.generate_key().decode()
    assert encrypt_value(None, key) is None
    assert encrypt_value("", key) is None
    assert encrypt_value("  ", key) is None


def test_decrypt_none_returns_none():
    """Decrypting None or empty string returns None."""
    key = Fernet.generate_key().decode()
    assert decrypt_value(None, key) is None
    assert decrypt_value("", key) is None
    assert decrypt_value("  ", key) is None


def test_empty_secret_fallback_plaintext():
    """When secret is empty, encrypt returns plaintext (fallback for migration)."""
    plain = "legacy-key"
    assert encrypt_value(plain, "") == plain
    assert encrypt_value(plain, "  ") == plain


def test_empty_secret_decrypt_returns_cipher_as_is():
    """When secret is empty, decrypt returns cipher as-is."""
    cipher = "some-stored-value"
    assert decrypt_value(cipher, "") == cipher
    assert decrypt_value(cipher, "  ") == cipher


def test_wrong_key_decrypt_returns_cipher_as_is():
    """When decrypting with wrong key, return cipher as-is (legacy plaintext or wrong key)."""
    key1 = Fernet.generate_key().decode()
    key2 = Fernet.generate_key().decode()
    plain = "secret"
    cipher = encrypt_value(plain, key1)
    assert cipher is not None
    # Decrypt with different key returns cipher unchanged (InvalidToken)
    assert decrypt_value(cipher, key2) == cipher


def test_invalid_fernet_key_encrypt_returns_plain():
    """When secret is not a valid Fernet key, encrypt returns plaintext."""
    plain = "my-key"
    assert encrypt_value(plain, "not-a-valid-fernet-key") == plain


def test_invalid_fernet_key_decrypt_returns_cipher():
    """When secret is not a valid Fernet key, decrypt returns cipher as-is."""
    cipher = "stored-value"
    assert decrypt_value(cipher, "not-a-valid-fernet-key") == cipher
