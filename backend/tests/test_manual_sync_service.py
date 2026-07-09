from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.models import AppUser, SourceConnection, SyncRun
from app.schemas.connectors import (
    BackfillSyncRequest,
    NormalizedRecord,
    ProviderPayload,
    SyncResult,
    SyncStatus,
)
from app.schemas.sync import ManualSyncRequest
from app.services.sync import (
    ManualSyncService,
    ManualSyncWindowError,
    SourceConnectionNotFoundError,
    SyncAlreadyRunningError,
)


class FakeGarminSyncService:
    def __init__(self, *, fail_step: str | None = None) -> None:
        self.fail_step = fail_step
        self.calls: list[str] = []
        self.requests: list[BackfillSyncRequest] = []

    def sync_backfill_activities(
        self,
        db: Session,
        request: BackfillSyncRequest,
    ) -> SyncResult:
        return self._result("activities", request)

    def sync_backfill_daily_metrics_and_sleep(
        self,
        db: Session,
        request: BackfillSyncRequest,
    ) -> SyncResult:
        return self._result("daily_sleep", request)

    def sync_backfill_biometrics(
        self,
        db: Session,
        request: BackfillSyncRequest,
    ) -> SyncResult:
        return self._result("biometrics", request)

    def _result(self, step: str, request: BackfillSyncRequest) -> SyncResult:
        self.calls.append(step)
        self.requests.append(request)
        if self.fail_step == step:
            return SyncResult(
                source_connection_id=request.source_connection_id,
                sync_run_id=request.sync_run_id,
                status=SyncStatus.FAILED,
                error_code="garmin_connection_retryable",
                error_message="Garmin sync failed due to a temporary provider error.",
            )
        return SyncResult(
            source_connection_id=request.source_connection_id,
            sync_run_id=request.sync_run_id,
            raw_payloads=[
                ProviderPayload(
                    object_type=step,
                    object_id=f"{step}-1",
                    observed_at=datetime(2026, 7, 9, 12, 0, tzinfo=UTC),
                    payload={"step": step},
                )
            ],
            normalized_records=[
                NormalizedRecord(
                    record_type="activity",
                    source_record_id=f"{step}-record-1",
                    data={},
                )
            ],
        )


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def _seed_user_and_connection(
    db: Session,
    *,
    status: str = "active",
) -> tuple[AppUser, SourceConnection]:
    user = AppUser(
        better_auth_user_id="better-auth-user-1",
        email="runner@example.com",
        display_name="Runner",
    )
    db.add(user)
    db.flush()
    connection = SourceConnection(
        user_id=user.id,
        source="garmin",
        status=status,
        provider_subject_id="garmin-user-1",
        display_name="Runner Garmin",
        connection_metadata={},
    )
    db.add(connection)
    db.commit()
    db.refresh(user)
    db.refresh(connection)
    return user, connection


def test_manual_sync_service_creates_sync_run_and_aggregates_counts(db: Session) -> None:
    user, connection = _seed_user_and_connection(db)
    garmin_service = FakeGarminSyncService()
    service = ManualSyncService(garmin_service)  # type: ignore[arg-type]

    sync_run = service.trigger_manual_sync(
        db,
        user,
        ManualSyncRequest(
            start_date=date(2026, 7, 3),
            end_date=date(2026, 7, 9),
        ),
    )

    assert sync_run.status == "succeeded"
    assert sync_run.sync_type == "manual"
    assert sync_run.source_connection_id == connection.id
    assert sync_run.records_seen == 3
    assert sync_run.records_imported == 3
    assert sync_run.window_start == datetime(2026, 7, 3, 0, 0)
    assert sync_run.window_end == datetime(2026, 7, 9, 23, 59, 59, 999999)
    assert garmin_service.calls == ["activities", "daily_sleep", "biometrics"]
    assert connection.last_sync_at == sync_run.completed_at
    assert db.scalar(select(SyncRun).where(SyncRun.id == sync_run.id)) is not None


def test_manual_sync_service_marks_run_failed_and_stops_after_connector_failure(
    db: Session,
) -> None:
    user, _connection = _seed_user_and_connection(db)
    garmin_service = FakeGarminSyncService(fail_step="daily_sleep")
    service = ManualSyncService(garmin_service)  # type: ignore[arg-type]

    sync_run = service.trigger_manual_sync(
        db,
        user,
        ManualSyncRequest(
            start_date=date(2026, 7, 3),
            end_date=date(2026, 7, 9),
        ),
    )

    assert sync_run.status == "failed"
    assert sync_run.error_code == "garmin_connection_retryable"
    assert sync_run.records_seen == 0
    assert garmin_service.calls == ["activities", "daily_sleep"]


def test_manual_sync_service_rejects_missing_connection(db: Session) -> None:
    user = AppUser(
        better_auth_user_id="better-auth-user-1",
        email="runner@example.com",
    )
    db.add(user)
    db.commit()
    service = ManualSyncService(FakeGarminSyncService())  # type: ignore[arg-type]

    with pytest.raises(SourceConnectionNotFoundError):
        service.trigger_manual_sync(db, user, ManualSyncRequest())


def test_manual_sync_service_rejects_duplicate_running_sync(db: Session) -> None:
    user, connection = _seed_user_and_connection(db)
    db.add(
        SyncRun(
            user_id=user.id,
            source_connection_id=connection.id,
            status="running",
            sync_type="manual",
        )
    )
    db.commit()
    service = ManualSyncService(FakeGarminSyncService())  # type: ignore[arg-type]

    with pytest.raises(SyncAlreadyRunningError):
        service.trigger_manual_sync(db, user, ManualSyncRequest())


def test_manual_sync_service_rejects_oversized_explicit_window(db: Session) -> None:
    user, _connection = _seed_user_and_connection(db)
    service = ManualSyncService(FakeGarminSyncService())  # type: ignore[arg-type]

    with pytest.raises(ManualSyncWindowError):
        service.trigger_manual_sync(
            db,
            user,
            ManualSyncRequest(
                start_date=date(2026, 6, 1),
                end_date=date(2026, 7, 9),
            ),
        )
