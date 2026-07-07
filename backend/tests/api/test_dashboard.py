from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_app_user
from app.db.models import Base
from app.db.session import get_db
from app.main import create_app
from app.models import (
    Activity,
    AppUser,
    CoachInsight,
    DailyMetric,
    SleepSession,
    SourceConnection,
    SyncRun,
)


def _create_client() -> tuple[TestClient, Session, AppUser, AppUser]:
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
    other_user = AppUser(
        better_auth_user_id="better-auth-user-2",
        email="other@example.com",
        display_name="Other Runner",
    )
    db.add_all([user, other_user])
    db.commit()
    db.refresh(user)
    db.refresh(other_user)

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_app_user] = lambda: user
    return TestClient(app), db, user, other_user


def test_dashboard_overview_returns_empty_summary_for_new_user() -> None:
    client, db, _user, _other_user = _create_client()

    try:
        response = client.get("/dashboard/overview")
    finally:
        db.close()

    assert response.status_code == 200
    assert response.json() == {
        "activity": {
            "activity_count_7d": 0,
            "duration_seconds_7d": 0,
            "distance_meters_7d": None,
            "latest_activity_date": None,
        },
        "recovery": {
            "metric_date": None,
            "steps": None,
            "active_seconds": None,
            "resting_heart_rate": None,
            "hrv_ms": None,
            "body_battery_latest": None,
            "stress_average": None,
        },
        "sleep": {
            "sleep_date": None,
            "total_sleep_seconds": None,
            "sleep_score": None,
            "average_hrv_ms": None,
        },
        "latest_insight": None,
        "sync": {
            "connected_sources": 0,
            "active_sources": 0,
            "latest_sync_status": None,
            "latest_sync_completed_at": None,
            "latest_sync_error_code": None,
        },
    }


def test_dashboard_overview_returns_current_user_summary() -> None:
    client, db, user, other_user = _create_client()
    today = datetime.now(UTC).date()
    now = datetime(2026, 7, 7, 10, 30, tzinfo=UTC)
    connection = SourceConnection(
        user_id=user.id,
        source="garmin",
        status="active",
        provider_subject_id="garmin-user-1",
        display_name="Runner Garmin",
        connection_metadata={},
        last_sync_at=now,
    )
    other_connection = SourceConnection(
        user_id=other_user.id,
        source="garmin",
        status="active",
        connection_metadata={},
    )
    db.add_all([connection, other_connection])
    db.flush()
    db.add_all(
        [
            Activity(
                user_id=user.id,
                source_connection_id=connection.id,
                source_activity_id="activity-1",
                activity_type="run",
                name="Easy run",
                activity_date=today,
                started_at=datetime(2026, 7, 7, 7, 0, tzinfo=UTC),
                duration_seconds=1800,
                distance_meters=Decimal("5000.50"),
                raw_data={},
            ),
            Activity(
                user_id=user.id,
                source_connection_id=connection.id,
                source_activity_id="activity-2",
                activity_type="ride",
                name="Spin",
                activity_date=today - timedelta(days=2),
                started_at=datetime(2026, 7, 5, 7, 0, tzinfo=UTC),
                duration_seconds=3600,
                distance_meters=Decimal("25000.00"),
                raw_data={},
            ),
            Activity(
                user_id=user.id,
                source_connection_id=connection.id,
                source_activity_id="old-activity",
                activity_type="run",
                activity_date=today - timedelta(days=10),
                started_at=datetime(2026, 6, 27, 7, 0, tzinfo=UTC),
                duration_seconds=9999,
                distance_meters=Decimal("9999.00"),
                raw_data={},
            ),
            Activity(
                user_id=other_user.id,
                source_connection_id=other_connection.id,
                source_activity_id="other-activity",
                activity_type="run",
                activity_date=today,
                started_at=datetime(2026, 7, 7, 8, 0, tzinfo=UTC),
                duration_seconds=9999,
                distance_meters=Decimal("9999.00"),
                raw_data={},
            ),
        ]
    )
    db.add(
        DailyMetric(
            user_id=user.id,
            source_connection_id=connection.id,
            metric_date=today,
            steps=12345,
            active_seconds=4200,
            resting_heart_rate=48,
            hrv_ms=Decimal("62.50"),
            body_battery_latest=76,
            stress_average=Decimal("22.40"),
            raw_data={},
        )
    )
    db.add(
        SleepSession(
            user_id=user.id,
            source_connection_id=connection.id,
            source_sleep_id="sleep-1",
            sleep_date=today,
            started_at=datetime(2026, 7, 6, 22, 30, tzinfo=UTC),
            ended_at=datetime(2026, 7, 7, 6, 30, tzinfo=UTC),
            total_sleep_seconds=28800,
            sleep_score=84,
            average_hrv_ms=Decimal("64.10"),
            raw_data={},
        )
    )
    db.add(
        SyncRun(
            user_id=user.id,
            source_connection_id=connection.id,
            status="succeeded",
            sync_type="manual",
            started_at=now,
            completed_at=now,
            records_seen=4,
            records_imported=4,
        )
    )
    db.add(
        CoachInsight(
            user_id=user.id,
            insight_date=today,
            insight_type="daily",
            title="Build steadily",
            summary="Training is consistent and recovery markers are solid.",
            recommendation="Keep the next run easy.",
            output={"readiness": "good"},
            generated_at=now,
        )
    )
    db.commit()

    try:
        response = client.get("/dashboard/overview")
    finally:
        db.close()

    assert response.status_code == 200
    body = response.json()
    assert body["activity"] == {
        "activity_count_7d": 2,
        "duration_seconds_7d": 5400,
        "distance_meters_7d": "30000.50",
        "latest_activity_date": today.isoformat(),
    }
    assert body["recovery"] == {
        "metric_date": today.isoformat(),
        "steps": 12345,
        "active_seconds": 4200,
        "resting_heart_rate": 48,
        "hrv_ms": "62.50",
        "body_battery_latest": 76,
        "stress_average": "22.40",
    }
    assert body["sleep"] == {
        "sleep_date": today.isoformat(),
        "total_sleep_seconds": 28800,
        "sleep_score": 84,
        "average_hrv_ms": "64.10",
    }
    assert body["latest_insight"] == {
        "id": body["latest_insight"]["id"],
        "insight_date": today.isoformat(),
        "insight_type": "daily",
        "title": "Build steadily",
        "summary": "Training is consistent and recovery markers are solid.",
        "recommendation": "Keep the next run easy.",
        "generated_at": "2026-07-07T10:30:00",
    }
    assert body["sync"] == {
        "connected_sources": 1,
        "active_sources": 1,
        "latest_sync_status": "succeeded",
        "latest_sync_completed_at": "2026-07-07T10:30:00",
        "latest_sync_error_code": None,
    }


def test_dashboard_overview_requires_authentication() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/dashboard/overview")

    assert response.status_code == 401
