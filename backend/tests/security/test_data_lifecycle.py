from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_app_user
from app.api.sync import get_manual_sync_service
from app.db.models import Base
from app.db.session import get_db
from app.main import create_app
from app.models import (
    Activity,
    AppUser,
    BiometricSample,
    CoachInsight,
    DailyMetric,
    RawObservation,
    SleepSession,
    SourceConnection,
    SyncRun,
)
from app.services.sync import ManualSyncService


class FailingGarminSyncService:
    def sync_backfill_activities(self, db: Session, request: object) -> object:
        raise AssertionError("Disconnected source should not reach Garmin sync")

    def sync_backfill_daily_metrics_and_sleep(self, db: Session, request: object) -> object:
        raise AssertionError("Disconnected source should not reach Garmin sync")

    def sync_backfill_biometrics(self, db: Session, request: object) -> object:
        raise AssertionError("Disconnected source should not reach Garmin sync")


def test_disconnect_garmin_prevents_future_manual_sync() -> None:
    client, db, user = _create_client_with_dataset()
    app = client.app
    app.dependency_overrides[get_manual_sync_service] = lambda: ManualSyncService(
        FailingGarminSyncService()
    )

    try:
        disconnect_response = client.delete("/connections/garmin")
        sync_response = client.post("/sync/manual", json={})
        connection = db.scalar(
            select(SourceConnection).where(
                SourceConnection.user_id == user.id,
                SourceConnection.source == "garmin",
            )
        )
    finally:
        db.close()

    assert disconnect_response.status_code == 200
    assert disconnect_response.json()["status"] == "disconnected"
    assert sync_response.status_code == 409
    assert sync_response.json() == {"detail": "Source connection is not active"}
    assert connection is not None
    assert connection.status == "disconnected"
    assert "session_material" not in connection.connection_metadata


def test_delete_synced_data_removes_current_user_records_and_keeps_connection() -> None:
    client, db, user = _create_client_with_dataset()

    try:
        response = client.delete("/users/me/data?source=garmin")
        own_counts = _record_counts(db, user_id=user.id)
        other_user = db.scalar(select(AppUser).where(AppUser.email == "other@example.com"))
        assert other_user is not None
        other_counts = _record_counts(db, user_id=other_user.id)
        connection = db.scalar(
            select(SourceConnection).where(
                SourceConnection.user_id == user.id,
                SourceConnection.source == "garmin",
            )
        )
    finally:
        db.close()

    assert response.status_code == 200
    assert response.json() == {
        "source": "garmin",
        "activities_deleted": 1,
        "daily_metrics_deleted": 1,
        "sleep_sessions_deleted": 1,
        "biometric_samples_deleted": 1,
        "raw_observations_deleted": 1,
        "sync_runs_deleted": 1,
        "coach_insights_deleted": 1,
        "total_deleted": 7,
    }
    assert own_counts == {
        "activities": 0,
        "daily_metrics": 0,
        "sleep_sessions": 0,
        "biometric_samples": 0,
        "raw_observations": 0,
        "sync_runs": 0,
        "coach_insights": 0,
        "source_connections": 1,
    }
    assert other_counts == {
        "activities": 1,
        "daily_metrics": 1,
        "sleep_sessions": 1,
        "biometric_samples": 1,
        "raw_observations": 1,
        "sync_runs": 1,
        "coach_insights": 1,
        "source_connections": 1,
    }
    assert connection is not None
    assert connection.status == "active"


def test_delete_account_data_removes_current_user_owned_records() -> None:
    client, db, user = _create_client_with_dataset()
    user_id = user.id

    try:
        response = client.delete("/users/me")
        own_user = db.get(AppUser, user_id)
        other_user = db.scalar(select(AppUser).where(AppUser.email == "other@example.com"))
        assert other_user is not None
        other_counts = _record_counts(db, user_id=other_user.id)
    finally:
        db.close()

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert response.json()["source_connections_deleted"] == 1
    assert response.json()["synced_records_deleted"] == 7
    assert response.json()["total_deleted"] == 9
    assert own_user is None
    assert other_counts == {
        "activities": 1,
        "daily_metrics": 1,
        "sleep_sessions": 1,
        "biometric_samples": 1,
        "raw_observations": 1,
        "sync_runs": 1,
        "coach_insights": 1,
        "source_connections": 1,
    }


def _create_client_with_dataset() -> tuple[TestClient, Session, AppUser]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = _add_user_dataset(
        db,
        better_auth_user_id="better-auth-user-1",
        email="runner@example.com",
        provider_subject_id="garmin-user-1",
        record_suffix="one",
    )
    _add_user_dataset(
        db,
        better_auth_user_id="better-auth-user-2",
        email="other@example.com",
        provider_subject_id="garmin-user-2",
        record_suffix="two",
    )
    db.commit()
    db.refresh(user)

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_app_user] = lambda: user
    return TestClient(app), db, user


def _add_user_dataset(
    db: Session,
    *,
    better_auth_user_id: str,
    email: str,
    provider_subject_id: str,
    record_suffix: str,
) -> AppUser:
    user = AppUser(
        better_auth_user_id=better_auth_user_id,
        email=email,
        display_name="Runner",
    )
    connection = SourceConnection(
        user=user,
        source="garmin",
        status="active",
        provider_subject_id=provider_subject_id,
        display_name="Runner Garmin",
        connection_metadata={
            "region": "global",
            "session_material": {"ciphertext": f"encrypted-{record_suffix}"},
        },
    )
    started_at = datetime(2026, 7, 9, 7, 30, tzinfo=UTC)
    ended_at = started_at + timedelta(minutes=45)
    sync_run = SyncRun(
        user=user,
        source_connection=connection,
        status="succeeded",
        sync_type="manual",
        started_at=started_at,
        completed_at=ended_at,
        records_seen=5,
        records_imported=5,
    )
    db.add_all(
        [
            Activity(
                user=user,
                source_connection=connection,
                source_activity_id=f"activity-{record_suffix}",
                activity_type="running",
                name="Morning Run",
                activity_date=date(2026, 7, 9),
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=2700,
                raw_data={"id": f"activity-{record_suffix}"},
            ),
            DailyMetric(
                user=user,
                source_connection=connection,
                metric_date=date(2026, 7, 9),
                steps=10000,
                raw_data={"date": "2026-07-09"},
            ),
            SleepSession(
                user=user,
                source_connection=connection,
                source_sleep_id=f"sleep-{record_suffix}",
                sleep_date=date(2026, 7, 9),
                started_at=datetime(2026, 7, 8, 22, 30, tzinfo=UTC),
                ended_at=datetime(2026, 7, 9, 6, 30, tzinfo=UTC),
                total_sleep_seconds=28800,
                raw_data={"id": f"sleep-{record_suffix}"},
            ),
            BiometricSample(
                user=user,
                source_connection=connection,
                source_sample_id=f"hr-{record_suffix}",
                sample_type="heart_rate",
                sampled_at=started_at,
                value=Decimal("142.000"),
                unit="bpm",
                raw_data={"id": f"hr-{record_suffix}"},
            ),
            RawObservation(
                user=user,
                source_connection=connection,
                sync_run=sync_run,
                provider_object_type="activity",
                provider_object_id=f"activity-{record_suffix}",
                observed_at=started_at,
                payload={"id": f"activity-{record_suffix}"},
            ),
            CoachInsight(
                user=user,
                source_sync_run=sync_run,
                insight_date=date(2026, 7, 9),
                insight_type="daily_recovery",
                title="Keep it easy",
                summary="Recovery is mixed.",
                recommendation="Keep training easy today.",
                schema_version="v1",
                model_provider="mock",
                model_name="deterministic-coach",
                prompt_version="daily-v1",
                input_fingerprint=f"sha256:{record_suffix}",
                output={"readiness": "moderate"},
                generated_at=started_at,
            ),
        ]
    )
    return user


def _record_counts(db: Session, *, user_id: object) -> dict[str, int]:
    return {
        "activities": _count(db, Activity, user_id),
        "daily_metrics": _count(db, DailyMetric, user_id),
        "sleep_sessions": _count(db, SleepSession, user_id),
        "biometric_samples": _count(db, BiometricSample, user_id),
        "raw_observations": _count(db, RawObservation, user_id),
        "sync_runs": _count(db, SyncRun, user_id),
        "coach_insights": _count(db, CoachInsight, user_id),
        "source_connections": _count(db, SourceConnection, user_id),
    }


def _count(db: Session, model: object, user_id: object) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id)))
