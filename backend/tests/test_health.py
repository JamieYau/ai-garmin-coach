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
