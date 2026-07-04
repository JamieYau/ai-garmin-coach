from datetime import UTC, date, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.models import AppUser, CoachInsight, RawObservation, SourceConnection, SyncRun


def test_raw_observation_and_coach_insight_records_persist() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    generated_at = datetime(2026, 7, 4, 8, 15, tzinfo=UTC)

    with Session(engine) as session:
        user = AppUser(
            better_auth_user_id="better-auth-user-3",
            email="coach@example.com",
            display_name="Coach User",
        )
        connection = SourceConnection(
            user=user,
            source="garmin",
            provider_subject_id="garmin-user-3",
            connection_metadata={"region": "gb"},
        )
        sync_run = SyncRun(
            user=user,
            source_connection=connection,
            status="succeeded",
            sync_type="scheduled",
            records_seen=1,
            records_imported=1,
        )
        raw_observation = RawObservation(
            user=user,
            source_connection=connection,
            sync_run=sync_run,
            provider_object_type="daily_summary",
            provider_object_id="2026-07-04",
            observed_at=generated_at,
            payload={"calendarDate": "2026-07-04", "steps": 12000},
            payload_hash="sha256:daily-summary",
        )
        coach_insight = CoachInsight(
            user=user,
            source_sync_run=sync_run,
            insight_date=date(2026, 7, 4),
            insight_type="daily_recovery",
            title="Keep today aerobic",
            summary="Training load is rising while recovery markers are mixed.",
            recommendation="Run easy or take a rest day.",
            schema_version="v1",
            model_provider="openai",
            model_name="gpt-5",
            prompt_version="daily-v1",
            input_fingerprint="sha256:coach-input",
            output={"readiness": "moderate", "actions": ["easy run"]},
            generated_at=generated_at,
        )

        session.add_all([raw_observation, coach_insight])
        session.commit()

    with Session(engine) as session:
        persisted_user = session.scalar(
            select(AppUser).where(AppUser.better_auth_user_id == "better-auth-user-3")
        )

        assert persisted_user is not None
        assert persisted_user.raw_observations[0].provider_object_id == "2026-07-04"
        assert persisted_user.raw_observations[0].payload["steps"] == 12000
        assert persisted_user.coach_insights[0].insight_type == "daily_recovery"
        assert persisted_user.coach_insights[0].output["readiness"] == "moderate"


def test_raw_observation_and_coach_insight_tables_define_expected_constraints() -> None:
    raw_observations = RawObservation.__table__
    coach_insights = CoachInsight.__table__

    assert raw_observations.c.user_id.foreign_keys
    assert raw_observations.c.source_connection_id.foreign_keys
    assert raw_observations.c.sync_run_id.foreign_keys
    assert raw_observations.c.provider_object_type.nullable is False
    assert raw_observations.c.provider_object_id.nullable is False
    assert raw_observations.c.payload.nullable is False
    assert coach_insights.c.user_id.foreign_keys
    assert coach_insights.c.source_sync_run_id.foreign_keys
    assert coach_insights.c.insight_date.nullable is False
    assert coach_insights.c.insight_type.nullable is False
    assert coach_insights.c.output.nullable is False
