from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
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
    app_component: Literal["api", "migration", "scheduled_job"] = "api"
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
    rate_limit_enabled: bool = True
    garmin_connection_rate_limit_max_requests: int = 5
    garmin_connection_rate_limit_window_seconds: int = 60
    manual_sync_rate_limit_max_requests: int = 3
    manual_sync_rate_limit_window_seconds: int = 60
    ai_insight_rate_limit_max_requests: int = 3
    ai_insight_rate_limit_window_seconds: int = 60

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.app_env.strip().lower() != "production":
            return self

        if not self.database_url:
            raise ValueError("DATABASE_URL is required in production")
        if not self.better_auth_secret or len(self.better_auth_secret) < 32:
            raise ValueError("BETTER_AUTH_SECRET must contain at least 32 characters in production")

        if self.app_component != "api":
            return self

        for setting_name, origin in (
            ("FRONTEND_URL", self.frontend_url),
            ("BETTER_AUTH_URL", self.better_auth_url),
        ):
            parsed_origin = urlparse(origin)
            if parsed_origin.scheme != "https" or not parsed_origin.netloc:
                raise ValueError(f"{setting_name} must be an absolute HTTPS origin in production")

        if not self.backend_cors_allow_credentials:
            raise ValueError("BACKEND_CORS_ALLOW_CREDENTIALS must be enabled in production")
        if self.backend_cors_origins != [self.frontend_url]:
            raise ValueError(
                "BACKEND_CORS_ORIGINS must contain exactly FRONTEND_URL in production"
            )
        if any(
            urlparse(origin).scheme != "https" or not urlparse(origin).netloc
            for origin in self.backend_cors_origins
        ):
            raise ValueError("BACKEND_CORS_ORIGINS must contain only absolute HTTPS origins")

        return self

    def require_database_url(self) -> str:
        if not self.database_url:
            raise ValueError("DATABASE_URL is required for database migrations")
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
