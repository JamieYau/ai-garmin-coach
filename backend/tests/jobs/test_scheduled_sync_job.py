from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.jobs.sync import run_scheduled_sync_job, run_scheduled_sync_job_once
from app.models import AppUser, SourceConnection, SyncRun
from app.schemas.connectors import (
    BackfillSyncRequest,
    ConnectorRecordType,
    NormalizedRecord,
    ProviderPayload,
    SyncResult,
    SyncStatus,
)
from app.services.sync import ScheduledSyncService


class FakeGarminSyncService:
    def __init__(
        self,
        *,
        fail_step: str | None = None,
        raise_value_error: bool = False,
    ) -> None:
        self.fail_step = fail_step
        self.raise_value_error = raise_value_error
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
        if self.raise_value_error:
            raise ValueError("missing tokenstore")
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
                    object_id=f"{step}-{request.source_connection_id}",
                    observed_at=datetime(2026, 7, 9, 12, 0, tzinfo=UTC),
                    payload={"step": step},
                )
            ],
            normalized_records=[
                NormalizedRecord(
                    record_type=ConnectorRecordType.ACTIVITY,
                    source_record_id=f"{step}-record-{request.source_connection_id}",
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


def _seed_connection(
    db: Session,
    *,
    better_auth_user_id: str,
    email: str,
    source: str = "garmin",
    status: str = "active",
    last_sync_at: datetime | None = None,
) -> tuple[AppUser, SourceConnection]:
    user = AppUser(
        better_auth_user_id=better_auth_user_id,
        email=email,
        display_name=email,
    )
    db.add(user)
    db.flush()
    connection = SourceConnection(
        user_id=user.id,
        source=source,
        status=status,
        provider_subject_id=f"provider-{better_auth_user_id}",
        display_name="Garmin",
        connection_metadata={},
        last_sync_at=last_sync_at,
    )
    db.add(connection)
    db.commit()
    db.refresh(user)
    db.refresh(connection)
    return user, connection


def test_scheduled_sync_job_runs_active_garmin_connections_and_skips_in_flight(
    db: Session,
) -> None:
    user, connection = _seed_connection(
        db,
        better_auth_user_id="better-auth-user-1",
        email="runner@example.com",
    )
    running_user, running_connection = _seed_connection(
        db,
        better_auth_user_id="better-auth-user-2",
        email="running@example.com",
    )
    _seed_connection(
        db,
        better_auth_user_id="better-auth-user-3",
        email="paused@example.com",
        status="paused",
    )
    _seed_connection(
        db,
        better_auth_user_id="better-auth-user-4",
        email="demo@example.com",
        source="demo",
    )
    db.add(
        SyncRun(
            user_id=running_user.id,
            source_connection_id=running_connection.id,
            status="running",
            sync_type="scheduled",
        )
    )
    db.commit()
    garmin_service = FakeGarminSyncService()
    service = ScheduledSyncService(garmin_service)

    result = run_scheduled_sync_job(db, service)

    assert result.started == 1
    assert result.succeeded == 1
    assert result.failed == 0
    assert result.skipped == 1
    assert garmin_service.calls == ["activities", "daily_sleep", "biometrics"]
    sync_run = db.scalar(
        select(SyncRun).where(
            SyncRun.user_id == user.id,
            SyncRun.source_connection_id == connection.id,
        )
    )
    assert sync_run is not None
    assert sync_run.id == result.sync_run_ids[0]
    assert sync_run.sync_type == "scheduled"
    assert sync_run.status == "succeeded"
    assert sync_run.records_seen == 3
    assert sync_run.records_imported == 3
    assert connection.last_sync_at == sync_run.completed_at


def test_scheduled_sync_job_records_connector_failure_and_stops_that_connection(
    db: Session,
) -> None:
    _user, connection = _seed_connection(
        db,
        better_auth_user_id="better-auth-user-1",
        email="runner@example.com",
    )
    garmin_service = FakeGarminSyncService(fail_step="daily_sleep")
    service = ScheduledSyncService(garmin_service)

    result = run_scheduled_sync_job(db, service)

    assert result.started == 1
    assert result.succeeded == 0
    assert result.failed == 1
    assert result.skipped == 0
    assert garmin_service.calls == ["activities", "daily_sleep"]
    sync_run = db.scalar(
        select(SyncRun).where(SyncRun.source_connection_id == connection.id)
    )
    assert sync_run is not None
    assert sync_run.status == "failed"
    assert sync_run.sync_type == "scheduled"
    assert sync_run.error_code == "garmin_connection_retryable"
    assert sync_run.completed_at is not None


def test_scheduled_sync_job_records_invalid_connection_without_raw_error(
    db: Session,
) -> None:
    _user, connection = _seed_connection(
        db,
        better_auth_user_id="better-auth-user-1",
        email="runner@example.com",
    )
    service = ScheduledSyncService(FakeGarminSyncService(raise_value_error=True))

    result = run_scheduled_sync_job(db, service)

    assert result.started == 1
    assert result.failed == 1
    sync_run = db.scalar(
        select(SyncRun).where(SyncRun.source_connection_id == connection.id)
    )
    assert sync_run is not None
    assert sync_run.status == "failed"
    assert sync_run.error_code == "scheduled_sync_invalid_connection"
    assert sync_run.error_message == "Sync could not use the configured source connection."


def test_scheduled_sync_job_once_uses_supplied_session_factory(db: Session) -> None:
    bind = db.get_bind()
    test_session_factory = sessionmaker(bind=bind, autocommit=False, autoflush=False)
    _seed_connection(
        db,
        better_auth_user_id="better-auth-user-1",
        email="runner@example.com",
    )
    service = ScheduledSyncService(FakeGarminSyncService())

    result = run_scheduled_sync_job_once(
        session_factory=test_session_factory,
        service=service,
    )

    assert result.started == 1
    assert result.succeeded == 1
