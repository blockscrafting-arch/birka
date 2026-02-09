"""Application settings from environment."""
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_int_list(value: str) -> List[int]:
    """Parse comma-separated integers from env string."""
    if not value or not value.strip():
        return []
    return [int(x.strip()) for x in value.strip().split(",") if x.strip().isdigit()]


def _parse_cors_origins(value: str) -> List[str]:
    """Parse comma-separated CORS origins from env string. '*' remains as single element."""
    if not value or not value.strip():
        return []
    parts = [x.strip() for x in value.strip().split(",") if x.strip()]
    return parts if parts else ["*"]


class Settings(BaseSettings):
    """Configuration loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Auth and admin
    ADMIN_TELEGRAM_IDS: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    OPENAI_API_KEY: str = ""

    # AI (defaults; can be overridden by admin ai_settings in DB)
    OPENROUTER_API_KEY: str = ""
    AI_PROVIDER: str = "openai"  # openai | openrouter
    AI_MODEL: str = "gpt-4o-mini"  # or e.g. openai/gpt-4o, anthropic/claude-3-sonnet for OpenRouter

    # Database
    POSTGRES_DSN: str = "postgresql+asyncpg://user:pass@localhost:5432/birka"

    # Redis (optional; for caching; empty = no cache)
    REDIS_DSN: str = ""

    # Shipment scheduler: интервал проверки просроченных отгрузок (секунды)
    SHIPMENT_SCHEDULER_INTERVAL_SECONDS: int = 600

    # CORS (comma-separated origins). В production запрещено "*" при allow_credentials.
    CORS_ORIGINS: str = "*"
    # Окружение: development | production. В production при CORS_ORIGINS=* приложение не стартует.
    ENVIRONMENT: str = "development"

    # Upload limits (bytes)
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # Encryption for API keys (Fernet key, base64 url-safe; generate with Fernet.generate_key())
    ENCRYPTION_KEY: str = ""

    # Dadata
    DADATA_TOKEN: str = ""

    # S3 (Beget etc.)
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "ru-1"
    S3_BUCKET_NAME: str = ""
    FILE_PUBLIC_BASE_URL: str = ""

    @property
    def admin_telegram_ids(self) -> List[int]:
        """Admin Telegram user IDs (parsed from ADMIN_TELEGRAM_IDS)."""
        return _parse_int_list(self.ADMIN_TELEGRAM_IDS)

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS allowed origins (parsed from CORS_ORIGINS comma-separated string)."""
        return _parse_cors_origins(self.CORS_ORIGINS)


settings = Settings()
