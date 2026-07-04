from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.models import (
    Activity,
    AppUser,
    BiometricSample,
    DailyMetric,
    SleepSession,
    SourceConnection,
)


def test_canonical_fitness_records_persist() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    started_at = datetime(2026, 7, 4, 7, 30, tzinfo=UTC)
    ended_at = started_at + timedelta(minutes=45)

    with Session(engine) as session:
        user = AppUser(
            better_auth_user_id="better-auth-user-2",
            email="fitness@example.com",
            display_name="Fitness User",
        )
        connection = SourceConnection(
            user=user,
            source="garmin",
            provider_subject_id="garmin-user-2",
            connection_metadata={"region": "gb"},
        )
        activity = Activity(
            user=user,
            source_connection=connection,
            source_activity_id="garmin-activity-1",
            activity_type="running",
            name="Morning Run",
            activity_date=date(2026, 7, 4),
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=2700,
            moving_duration_seconds=2650,
            distance_meters=Decimal("10000.00"),
            calories=650,
            average_heart_rate=151,
            max_heart_rate=176,
            raw_data={"activityId": 1},
        )
        daily_metric = DailyMetric(
            user=user,
            source_connection=connection,
            metric_date=date(2026, 7, 4),
            steps=12000,
            calories=2400,
            active_seconds=3600,
            highly_active_seconds=2700,
            resting_heart_rate=58,
            hrv_ms=Decimal("52.40"),
            raw_data={"calendarDate": "2026-07-04"},
        )
        sleep_session = SleepSession(
            user=user,
            source_connection=connection,
            source_sleep_id="garmin-sleep-1",
            sleep_date=date(2026, 7, 4),
            started_at=datetime(2026, 7, 3, 22, 45, tzinfo=UTC),
            ended_at=datetime(2026, 7, 4, 6, 30, tzinfo=UTC),
            total_sleep_seconds=26100,
            deep_sleep_seconds=5220,
            rem_sleep_seconds=6900,
            light_sleep_seconds=12180,
            awake_seconds=1800,
            sleep_score=78,
            average_spo2=Decimal("96.20"),
            average_hrv_ms=Decimal("48.00"),
            raw_data={"sleepStartTimestampGMT": "2026-07-03T21:45:00Z"},
        )
        biometric_sample = BiometricSample(
            user=user,
            source_connection=connection,
            source_sample_id="garmin-hr-1",
            sample_type="heart_rate",
            sampled_at=started_at,
            value=Decimal("142.000"),
            unit="bpm",
            aggregation_window_seconds=60,
            raw_data={"sample": "heart-rate"},
        )

        session.add_all([activity, daily_metric, sleep_session, biometric_sample])
        session.commit()

    with Session(engine) as session:
        persisted_user = session.scalar(
            select(AppUser).where(AppUser.better_auth_user_id == "better-auth-user-2")
        )

        assert persisted_user is not None
        assert persisted_user.activities[0].source_activity_id == "garmin-activity-1"
        assert persisted_user.activities[0].distance_meters == Decimal("10000.00")
        assert persisted_user.daily_metrics[0].steps == 12000
        assert persisted_user.sleep_sessions[0].sleep_score == 78
        assert persisted_user.biometric_samples[0].value == Decimal("142.000")


def test_canonical_fitness_tables_define_expected_constraints() -> None:
    activities = Activity.__table__
    daily_metrics = DailyMetric.__table__
    sleep_sessions = SleepSession.__table__
    biometric_samples = BiometricSample.__table__

    assert activities.c.user_id.foreign_keys
    assert activities.c.source_connection_id.foreign_keys
    assert activities.c.source_activity_id.nullable is False
    assert activities.c.raw_data.nullable is False
    assert daily_metrics.c.metric_date.nullable is False
    assert daily_metrics.c.raw_data.nullable is False
    assert sleep_sessions.c.source_sleep_id.nullable is False
    assert sleep_sessions.c.total_sleep_seconds.nullable is False
    assert biometric_samples.c.sample_type.nullable is False
    assert biometric_samples.c.value.nullable is False
    assert biometric_samples.c.raw_data.nullable is False
