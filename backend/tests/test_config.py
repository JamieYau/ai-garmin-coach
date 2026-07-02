from app.core.config import get_settings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/app")
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
