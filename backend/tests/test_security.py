"""Security tests."""
from app.core.security import validate_telegram_init_data


def test_validate_telegram_init_data_rejects_old_auth_date():
    """Reject init_data when auth_date is older than max_age_seconds."""
    # auth_date=1 is far in the past; HMAC is not checked when auth_date fails
    old_init_data = "auth_date=1&hash=abc"
    assert validate_telegram_init_data(old_init_data, max_age_seconds=300) is False


def test_validate_telegram_init_data_rejects_empty():
    """Reject empty init_data."""
    assert validate_telegram_init_data("") is False
