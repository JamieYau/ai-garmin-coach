from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.connections import get_garmin_connection_service
from app.api.dependencies import get_current_app_user
from app.api.sync import get_manual_sync_service
from app.db.models import Base
from app.db.session import get_db
from app.main import create_app
from app.middleware.rate_limit import RateLimitMiddleware, RateLimitRule
from app.middleware.request_id import REQUEST_ID_HEADER
from app.models import AppUser, SourceConnection, SyncRun
from app.schemas.connections import ConnectionResponse, GarminConnectionCreate
from app.schemas.sync import ManualSyncRequest


class FakeGarminConnectionService:
    def setup_connection(
        self,
        db: Session,
        user: AppUser,
        request: GarminConnectionCreate,
    ) -> ConnectionResponse:
        return ConnectionResponse(
            id="00000000-0000-0000-0000-000000000001",
            source="garmin",
            status="active",
            provider_subject_id="garmin-user-1",
            display_name="Runner Garmin",
        )


class FakeManualSyncService:
    def trigger_manual_sync(
        self,
        db: Session,
        user: AppUser,
        request: ManualSyncRequest,
    ) -> SyncRun:
        connection = db.scalar(
            select(SourceConnection).where(
                SourceConnection.user_id == user.id,
                SourceConnection.source == request.source,
            )
        )
        assert connection is not None
        now = datetime(2026, 7, 9, 12, 30, tzinfo=UTC)
        sync_run = SyncRun(
            user_id=user.id,
            source_connection_id=connection.id,
            status="succeeded",
            sync_type="manual",
            started_at=now,
            completed_at=now,
            window_start=datetime(2026, 7, 3, 0, 0, tzinfo=UTC),
            window_end=datetime(2026, 7, 9, 23, 59, 59, tzinfo=UTC),
            records_seen=5,
            records_imported=4,
        )
        db.add(sync_run)
        db.commit()
        db.refresh(sync_run)
        return sync_run


def test_request_id_middleware_generates_response_header() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER]


def test_request_id_middleware_preserves_valid_incoming_header() -> None:
    client = TestClient(create_app())

    response = client.get("/health", headers={REQUEST_ID_HEADER: "trace-123"})

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "trace-123"


def test_garmin_connection_attempts_are_rate_limited(monkeypatch) -> None:
    monkeypatch.setenv("GARMIN_CONNECTION_RATE_LIMIT_MAX_REQUESTS", "1")
    monkeypatch.setenv("GARMIN_CONNECTION_RATE_LIMIT_WINDOW_SECONDS", "60")
    client, db = _create_authenticated_client()

    try:
        first = client.post(
            "/connections/garmin",
            json={"username": "runner@example.com", "password": "garmin-password"},
        )
        second = client.post(
            "/connections/garmin",
            json={"username": "runner@example.com", "password": "garmin-password"},
        )
    finally:
        db.close()

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json() == {"detail": "Rate limit exceeded"}
    assert second.headers["Retry-After"] == "60"
    assert second.headers["X-RateLimit-Limit"] == "1"
    assert second.headers[REQUEST_ID_HEADER]


def test_manual_sync_requests_are_rate_limited(monkeypatch) -> None:
    monkeypatch.setenv("MANUAL_SYNC_RATE_LIMIT_MAX_REQUESTS", "1")
    monkeypatch.setenv("MANUAL_SYNC_RATE_LIMIT_WINDOW_SECONDS", "60")
    client, db = _create_authenticated_client()

    try:
        first = client.post("/sync/manual", json={})
        second = client.post("/sync/manual", json={})
    finally:
        db.close()

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json() == {"detail": "Rate limit exceeded"}
    assert second.headers["X-RateLimit-Limit"] == "1"
    assert second.headers[REQUEST_ID_HEADER]


def test_ai_insight_generation_route_pattern_is_rate_limited() -> None:
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        rules=(
            RateLimitRule(
                name="ai_insight_generation",
                method="POST",
                path="/coach/insights/generate",
                max_requests=1,
                window_seconds=60,
            ),
        ),
    )

    @app.post("/coach/insights/generate")
    def generate_insight() -> dict[str, str]:
        return {"status": "queued"}

    client = TestClient(app)

    first = client.post("/coach/insights/generate")
    second = client.post("/coach/insights/generate")

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json() == {"detail": "Rate limit exceeded"}


def _create_authenticated_client() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = AppUser(
        better_auth_user_id="better-auth-user-1",
        email="runner@example.com",
        display_name="Runner",
    )
    db.add(user)
    db.flush()
    db.add(
        SourceConnection(
            user_id=user.id,
            source="garmin",
            status="active",
            provider_subject_id="garmin-user-1",
            display_name="Runner Garmin",
            connection_metadata={},
        )
    )
    db.commit()
    db.refresh(user)

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_app_user] = lambda: user
    app.dependency_overrides[get_garmin_connection_service] = lambda: FakeGarminConnectionService()
    app.dependency_overrides[get_manual_sync_service] = lambda: FakeManualSyncService()
    return TestClient(app), db
