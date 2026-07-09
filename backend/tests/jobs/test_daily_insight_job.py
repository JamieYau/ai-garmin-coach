from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.ai.mock import MockCoachProvider
from app.db.models import Base
from app.jobs.coach import run_daily_insight_job_for_sync_runs
from app.models import Activity, AppUser, CoachInsight, SourceConnection, SyncRun


def _create_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed_user_connection_and_sync(
    session: Session,
    *,
    status: str,
    email: str = "runner@example.com",
) -> tuple[AppUser, SourceConnection, SyncRun]:
    user = AppUser(
        better_auth_user_id=email,
        email=email,
        display_name=email,
    )
    connection = SourceConnection(
        user=user,
        source="garmin",
        status="active",
        connection_metadata={},
    )
    sync_run = SyncRun(
        user=user,
        source_connection=connection,
        status=status,
        sync_type="scheduled",
        completed_at=datetime(2026, 7, 9, 8, 15, tzinfo=UTC),
        window_start=datetime(2026, 7, 3, 0, 0, tzinfo=UTC),
        window_end=datetime(2026, 7, 9, 23, 59, 59, tzinfo=UTC),
        records_seen=3,
        records_imported=3,
        error_code="garmin_connection_retryable" if status == "failed" else None,
    )
    session.add_all([user, connection, sync_run])
    session.flush()
    return user, connection, sync_run


def _seed_activity(
    session: Session,
    *,
    user: AppUser,
    connection: SourceConnection,
) -> None:
    session.add(
        Activity(
            user_id=user.id,
            source_connection_id=connection.id,
            source_activity_id="activity-1",
            activity_type="run",
            activity_date=date(2026, 7, 9),
            started_at=datetime(2026, 7, 9, 7, 0, tzinfo=UTC),
            duration_seconds=1800,
            distance_meters=Decimal("5000.00"),
            raw_data={},
        )
    )


def test_daily_insight_job_generates_for_successful_sync_and_links_source() -> None:
    session = _create_session()
    try:
        user, connection, sync_run = _seed_user_connection_and_sync(
            session,
            status="succeeded",
        )
        user_id = user.id
        sync_run_id = sync_run.id
        _seed_activity(session, user=user, connection=connection)
        session.commit()

        result = run_daily_insight_job_for_sync_runs(
            session,
            sync_runs=(sync_run,),
            provider=MockCoachProvider(),
        )
        persisted_count = session.scalar(select(func.count()).select_from(CoachInsight))
        coach_insight = session.scalar(select(CoachInsight))
    finally:
        session.close()

    assert result.attempted == 1
    assert result.generated == 1
    assert result.failed == 0
    assert result.skipped_sync_runs == 0
    assert persisted_count == 1
    assert coach_insight is not None
    assert result.coach_insight_ids == (coach_insight.id,)
    assert coach_insight.user_id == user_id
    assert coach_insight.source_sync_run_id == sync_run_id
    assert coach_insight.insight_date == date(2026, 7, 9)


def test_daily_insight_job_skips_failed_sync_without_new_insight() -> None:
    session = _create_session()
    try:
        _user, _connection, failed_sync = _seed_user_connection_and_sync(
            session,
            status="failed",
        )
        session.commit()

        result = run_daily_insight_job_for_sync_runs(
            session,
            sync_runs=(failed_sync,),
            provider=MockCoachProvider(),
        )
        persisted_count = session.scalar(select(func.count()).select_from(CoachInsight))
    finally:
        session.close()

    assert result.attempted == 0
    assert result.generated == 0
    assert result.failed == 0
    assert result.skipped_sync_runs == 1
    assert persisted_count == 0


def test_daily_insight_job_replaces_same_day_insight_after_later_success() -> None:
    session = _create_session()
    try:
        user, connection, first_sync = _seed_user_connection_and_sync(
            session,
            status="succeeded",
        )
        second_sync = SyncRun(
            user=user,
            source_connection=connection,
            status="succeeded",
            sync_type="scheduled",
            completed_at=datetime(2026, 7, 9, 10, 15, tzinfo=UTC),
            window_start=datetime(2026, 7, 9, 0, 0, tzinfo=UTC),
            window_end=datetime(2026, 7, 9, 23, 59, 59, tzinfo=UTC),
            records_seen=1,
            records_imported=1,
        )
        session.add(second_sync)
        session.flush()
        second_sync_id = second_sync.id
        session.commit()

        first = run_daily_insight_job_for_sync_runs(
            session,
            sync_runs=(first_sync,),
            provider=MockCoachProvider(),
        )
        second = run_daily_insight_job_for_sync_runs(
            session,
            sync_runs=(second_sync,),
            provider=MockCoachProvider(),
        )
        persisted_count = session.scalar(select(func.count()).select_from(CoachInsight))
        coach_insight = session.scalar(select(CoachInsight))
    finally:
        session.close()

    assert first.generated == 1
    assert second.generated == 1
    assert persisted_count == 1
    assert coach_insight is not None
    assert coach_insight.id == first.coach_insight_ids[0]
    assert coach_insight.id == second.coach_insight_ids[0]
    assert coach_insight.source_sync_run_id == second_sync_id
