from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.connectors.garmin.sync import GarminActivitySyncService
from app.core.security import encrypt_json_payload
from app.db.models import Base
from app.models import Activity, AppUser, RawObservation, SourceConnection, SyncRun
from app.schemas.connectors import BackfillSyncRequest, ConnectorRecordType, SyncStatus


class FakeGarminActivityClient:
    def __init__(self, activities: list[dict[str, Any]]) -> None:
        self.activities = activities
        self.login_tokenstore: str | None = None
        self.requested_window: tuple[date, date | None, str | None] | None = None

    def login(self, *, tokenstore: str | None = None) -> object:
        self.login_tokenstore = tokenstore
        return object()

    def get_activities_by_date(
        self,
        *,
        start_date: date,
        end_date: date | None = None,
        activity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        self.requested_window = (start_date, end_date, activity_type)
        return self.activities


def _create_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _activity_payload(activity_id: int, *, name: str = "Morning Run") -> dict[str, Any]:
    return {
        "activityId": activity_id,
        "activityName": name,
        "activityType": {"typeKey": "running"},
        "startTimeGMT": "2026-07-05T07:30:00Z",
        "duration": 2700,
        "movingDuration": 2640,
        "distance": 10000.12,
        "calories": 642,
        "averageHR": 151,
        "maxHR": 176,
        "trainingLoad": 82.25,
    }


def _seed_sync_context(session: Session) -> tuple[AppUser, SourceConnection, SyncRun]:
    user = AppUser(
        better_auth_user_id="better-auth-user-activity-sync",
        email="runner@example.com",
        display_name="Runner",
    )
    connection = SourceConnection(
        user=user,
        source="garmin",
        status="active",
        provider_subject_id="123",
        display_name="Runner",
        connection_metadata={
            "region": "global",
            "session_material": encrypt_json_payload(
                {"tokenstore": "serialized-tokenstore"},
                "test-secret",
            ),
            "session_material_type": "garminconnect_tokenstore",
        },
    )
    sync_run = SyncRun(
        user=user,
        source_connection=connection,
        status="queued",
        sync_type="backfill",
    )
    session.add(sync_run)
    session.commit()
    session.refresh(user)
    session.refresh(connection)
    session.refresh(sync_run)
    return user, connection, sync_run


def test_garmin_activity_sync_fetches_and_persists_activity_records() -> None:
    with _create_session() as session:
        user, connection, sync_run = _seed_sync_context(session)
        fake_client = FakeGarminActivityClient([_activity_payload(1001)])
        service = GarminActivitySyncService(
            encryption_secret="test-secret",
            client_builder=lambda is_cn: fake_client,
        )

        result = service.sync_backfill_activities(
            session,
            BackfillSyncRequest(
                user_id=user.id,
                source_connection_id=connection.id,
                sync_run_id=sync_run.id,
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 5),
            ),
        )

        activity = session.scalar(select(Activity).where(Activity.source_activity_id == "1001"))
        raw_observation = session.scalar(
            select(RawObservation).where(RawObservation.provider_object_id == "1001")
        )
        session.refresh(sync_run)

        assert fake_client.login_tokenstore == "serialized-tokenstore"
        assert fake_client.requested_window == (date(2026, 7, 1), date(2026, 7, 5), None)
        assert result.status is SyncStatus.SUCCEEDED
        assert result.raw_payload_count == 1
        assert result.normalized_record_count == 1
        assert result.normalized_records[0].record_type is ConnectorRecordType.ACTIVITY
        assert activity is not None
        assert activity.user_id == user.id
        assert activity.source_connection_id == connection.id
        assert activity.name == "Morning Run"
        assert activity.activity_date == date(2026, 7, 5)
        assert activity.started_at.replace(tzinfo=UTC) == datetime(
            2026,
            7,
            5,
            7,
            30,
            tzinfo=UTC,
        )
        assert activity.distance_meters == Decimal("10000.12")
        assert activity.training_load == Decimal("82.25")
        assert raw_observation is not None
        assert raw_observation.sync_run_id == sync_run.id
        assert raw_observation.payload["activityName"] == "Morning Run"
        assert raw_observation.payload_hash is not None
        assert sync_run.status == "succeeded"
        assert sync_run.records_seen == 1
        assert sync_run.records_imported == 1


def test_garmin_activity_sync_is_idempotent_for_existing_provider_activity() -> None:
    with _create_session() as session:
        user, connection, sync_run = _seed_sync_context(session)
        fake_client = FakeGarminActivityClient([_activity_payload(1001)])
        service = GarminActivitySyncService(
            encryption_secret="test-secret",
            client_builder=lambda is_cn: fake_client,
        )
        request = BackfillSyncRequest(
            user_id=user.id,
            source_connection_id=connection.id,
            sync_run_id=sync_run.id,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 5),
        )

        service.sync_backfill_activities(session, request)
        fake_client.activities = [_activity_payload(1001, name="Updated Run")]
        service.sync_backfill_activities(session, request)

        activities = session.scalars(select(Activity)).all()
        raw_observations = session.scalars(select(RawObservation)).all()

        assert len(activities) == 1
        assert activities[0].name == "Updated Run"
        assert len(raw_observations) == 1
        assert raw_observations[0].payload["activityName"] == "Updated Run"


def test_garmin_activity_sync_rejects_missing_connection_or_sync_run() -> None:
    with _create_session() as session:
        user, connection, sync_run = _seed_sync_context(session)
        service = GarminActivitySyncService(
            encryption_secret="test-secret",
            client_builder=lambda is_cn: FakeGarminActivityClient([]),
        )

        missing_connection_request = BackfillSyncRequest(
            user_id=user.id,
            source_connection_id=uuid4(),
            sync_run_id=sync_run.id,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 5),
        )
        missing_sync_run_request = BackfillSyncRequest(
            user_id=user.id,
            source_connection_id=connection.id,
            sync_run_id=uuid4(),
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 5),
        )

        with pytest.raises(ValueError, match="source connection"):
            service.sync_backfill_activities(session, missing_connection_request)

        with pytest.raises(ValueError, match="Sync run"):
            service.sync_backfill_activities(session, missing_sync_run_request)
