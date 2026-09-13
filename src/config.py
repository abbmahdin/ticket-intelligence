"""
Configuration settings for Ticket Intelligence.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://ticket_user:ticket_pass@localhost:5432/ticket_intelligence"
    DATABASE_URL_SYNC: str = "postgresql://ticket_user:ticket_pass@localhost:5432/ticket_intelligence"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Application
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key"

    # External APIs
    TICKETMASTER_API_KEY: str = ""
    SONGKICK_API_KEY: str = ""

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()