from app.core.config import Settings, get_settings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/app")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("OPENAI_MAX_OUTPUT_TOKENS", "900")
    monkeypatch.setenv(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:3001",
    )

    settings = get_settings()

    assert settings.app_env == "test"
    assert settings.database_url == "postgresql+psycopg://user:pass@localhost:5432/app"
    assert settings.backend_cors_origins == [
        "http://localhost:3000",
        "http://localhost:3001",
    ]
    assert settings.backend_cors_allow_credentials is True
    assert settings.openai_model == "gpt-test"
    assert settings.openai_max_output_tokens == 900


def test_require_database_url_rejects_missing_value(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")

    settings = get_settings()

    try:
        settings.require_database_url()
    except ValueError as error:
        assert str(error) == "DATABASE_URL is required for database migrations"
    else:
        raise AssertionError("Expected missing database URL to raise")


def test_production_settings_require_https_origins_and_a_strong_auth_secret() -> None:
    settings = Settings(
        app_env="production",
        database_url="postgresql+psycopg://user:pass@database.example:5432/app?sslmode=require",
        better_auth_secret="a" * 32,
        frontend_url="https://frontend.example",
        better_auth_url="https://frontend.example",
        backend_cors_origins=["https://frontend.example"],
        backend_cors_allow_credentials=True,
    )

    assert settings.app_env == "production"


def test_production_settings_reject_insecure_cors_and_missing_auth_secret() -> None:
    try:
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://user:pass@database.example:5432/app?sslmode=require",
            better_auth_secret="too-short",
            frontend_url="http://frontend.example",
            better_auth_url="https://frontend.example",
            backend_cors_origins=["*"],
            backend_cors_allow_credentials=False,
        )
    except ValueError as error:
        assert "BETTER_AUTH_SECRET" in str(error)
    else:
        raise AssertionError("Expected insecure production settings to be rejected")
