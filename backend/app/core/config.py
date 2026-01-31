"""Application settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Project configuration loaded from environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    PROJECT_NAME: str = "Birka"
    API_BASE_URL: str = "http://localhost:8000"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    POSTGRES_DSN: str = "postgresql+asyncpg://birka:birka@localhost:5432/birka"
    REDIS_DSN: str = "redis://localhost:6379/0"

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBAPP_SECRET: str = ""

    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = "ru-1"

    DADATA_TOKEN: str = ""
    OPENAI_API_KEY: str = ""

    FILE_PUBLIC_BASE_URL: str = ""
    MAX_UPLOAD_SIZE_BYTES: int = 20 * 1024 * 1024
    ADMIN_TELEGRAM_IDS: list[int] = []


settings = Settings()
