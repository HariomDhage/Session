"""Application configuration settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Session Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database - supports both local PostgreSQL and Supabase
    # For Supabase: postgresql+asyncpg://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
    # For local: postgresql+asyncpg://postgres:postgres@db:5432/sessions
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/sessions"

    # External Services
    WEBHOOK_URL: str = "http://mock_webhook:8001/webhook"
    WEBHOOK_TIMEOUT: int = 10
    WEBHOOK_ENABLED: bool = True

    # Session Settings
    MAX_SESSION_DURATION_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
