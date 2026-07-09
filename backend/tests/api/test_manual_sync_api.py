from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_app_user
from app.api.sync import get_manual_sync_service
from app.db.models import Base
from app.db.session import get_db
from app.main import create_app
from app.models import AppUser, SourceConnection, SyncRun
from app.schemas.sync import ManualSyncRequest
from app.services.sync import (
    SourceConnectionNotFoundError,
    SyncAlreadyRunningError,
    UnsupportedSyncSourceError,
)


class FakeManualSyncService:
    def __init__(
        self,
        status: str = "succeeded",
        error: Exception | None = None,
    ) -> None:
        self.status = status
        self.error = error
        self.seen_request: ManualSyncRequest | None = None

    def trigger_manual_sync(
        self,
        db: Session,
        user: AppUser,
        request: ManualSyncRequest,
    ) -> SyncRun:
        self.seen_request = request
        if self.error is not None:
            raise self.error
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
            status=self.status,
            sync_type="manual",
            started_at=now,
            completed_at=now,
            window_start=datetime(2026, 7, 3, 0, 0, tzinfo=UTC),
            window_end=datetime(2026, 7, 9, 23, 59, 59, tzinfo=UTC),
            records_seen=5,
            records_imported=4,
            error_code=None if self.status == "succeeded" else "garmin_connection_retryable",
        )
        db.add(sync_run)
        db.commit()
        db.refresh(sync_run)
        return sync_run


def _create_client(
    service: FakeManualSyncService | None = None,
    *,
    with_connection: bool = True,
) -> tuple[TestClient, Session, AppUser, FakeManualSyncService]:
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
    if with_connection:
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

    fake_service = service or FakeManualSyncService()

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_app_user] = lambda: user
    app.dependency_overrides[get_manual_sync_service] = lambda: fake_service
    return TestClient(app), db, user, fake_service


def test_manual_sync_endpoint_triggers_authenticated_user_sync() -> None:
    client, db, _user, service = _create_client()

    try:
        response = client.post("/sync/manual", json={})
    finally:
        db.close()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["sync_type"] == "manual"
    assert body["records_seen"] == 5
    assert body["records_imported"] == 4
    assert body["error_code"] is None
    assert service.seen_request == ManualSyncRequest(source="garmin")


def test_manual_sync_endpoint_returns_failed_run_without_raw_payloads() -> None:
    client, db, _user, _service = _create_client(FakeManualSyncService(status="failed"))

    try:
        response = client.post("/sync/manual", json={"source": "garmin"})
    finally:
        db.close()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_code"] == "garmin_connection_retryable"
    assert "error_message" not in body
    assert "raw_payloads" not in body


def test_manual_sync_endpoint_requires_authentication() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post("/sync/manual", json={})

    assert response.status_code == 401


def test_manual_sync_endpoint_rejects_unsupported_source() -> None:
    client, db, _user, _service = _create_client(
        FakeManualSyncService(error=UnsupportedSyncSourceError())
    )

    try:
        response = client.post("/sync/manual", json={"source": "strava"})
    finally:
        db.close()

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported sync source"}


def test_manual_sync_endpoint_returns_not_found_without_connection() -> None:
    client, db, _user, _service = _create_client(
        FakeManualSyncService(error=SourceConnectionNotFoundError()),
        with_connection=False,
    )

    try:
        response = client.post("/sync/manual", json={})
    finally:
        db.close()

    assert response.status_code == 404
    assert response.json() == {"detail": "Source connection not found"}


def test_manual_sync_endpoint_rejects_duplicate_running_sync() -> None:
    client, db, _user, _service = _create_client(
        FakeManualSyncService(error=SyncAlreadyRunningError())
    )

    try:
        response = client.post("/sync/manual", json={})
    finally:
        db.close()

    assert response.status_code == 409
    assert response.json() == {"detail": "A sync is already queued or running"}
