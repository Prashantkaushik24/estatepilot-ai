"""Application settings (env driven). All timestamps are stored in UTC."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_VERSION: str = "1.0.0"
    DATABASE_URL: str = "sqlite:///./estatepilot.db"
    SECRET_KEY: str = "change-me-in-production-please-use-a-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    BCRYPT_ROUNDS: int = 12
    DEMO_MODE: bool = True
    SEED_DEMO: bool = True
    AUTO_CREATE_TABLES: bool = True  # convenience for SQLite dev; use Alembic in prod

    AI_PROVIDER: str = "demo"  # demo | openai | gemini
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    AI_MAX_RETRIES: int = 2

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/integrations/gmail/callback"
    SENDING_ENABLED: bool = False

    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    POWERBI_EMBED_URL: str = ""
    POWERBI_REPORT_ID: str = ""
    POWERBI_WORKSPACE_ID: str = ""
    POWERBI_EMBED_ENABLED: bool = False

    TIMEZONE: str = "UTC"  # display hint only; everything stored/serialized as UTC
    LOGIN_RATE_LIMIT: int = 10  # attempts per window per ip+email
    LOGIN_RATE_WINDOW_SECONDS: int = 60

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
