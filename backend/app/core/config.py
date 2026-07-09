from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Garmin Coach API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "info"

    frontend_url: str = "http://localhost:3000"
    backend_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    backend_cors_allow_credentials: bool = True
    database_url: str | None = None

    better_auth_url: str = "http://localhost:3000"
    better_auth_secret: str | None = None
    ai_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.5"
    openai_max_output_tokens: int = 1200

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def require_database_url(self) -> str:
        if not self.database_url:
            raise ValueError("DATABASE_URL is required for database migrations")
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
