from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_reports_service_status(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "AI Garmin Coach API",
        "environment": "test",
    }


def test_ready_endpoint_allows_unconfigured_database(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "not_configured"}


def test_cors_allows_configured_frontend_origin(monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:3000")
    client = TestClient(create_app())

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"
