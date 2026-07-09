from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.models import Activity, AppUser, DailyMetric, SleepSession, SourceConnection
from app.schemas.coach import CoachMetricTrend
from app.services.metric_summary import build_coach_metric_summary


def _create_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _create_user_and_connection(
    session: Session,
    *,
    suffix: str,
) -> tuple[AppUser, SourceConnection]:
    user = AppUser(
        better_auth_user_id=f"better-auth-{suffix}",
        email=f"{suffix}@example.com",
        display_name=f"Runner {suffix}",
    )
    connection = SourceConnection(
        user=user,
        source="garmin",
        status="active",
        connection_metadata={},
    )
    session.add_all([user, connection])
    session.flush()
    return user, connection


def _add_activity(
    session: Session,
    *,
    user: AppUser,
    connection: SourceConnection,
    source_id: str,
    activity_date: date,
    duration_seconds: int,
    distance_meters: Decimal | None = None,
    training_load: Decimal | None = None,
    average_heart_rate: int | None = None,
) -> None:
    session.add(
        Activity(
            user_id=user.id,
            source_connection_id=connection.id,
            source_activity_id=source_id,
            activity_type="run",
            activity_date=activity_date,
            started_at=datetime.combine(activity_date, datetime.min.time(), tzinfo=UTC),
            duration_seconds=duration_seconds,
            distance_meters=distance_meters,
            training_load=training_load,
            average_heart_rate=average_heart_rate,
            raw_data={},
        )
    )


def _add_sleep(
    session: Session,
    *,
    user: AppUser,
    connection: SourceConnection,
    source_id: str,
    sleep_date: date,
    total_sleep_seconds: int,
    sleep_score: int | None = None,
    average_hrv_ms: Decimal | None = None,
) -> None:
    session.add(
        SleepSession(
            user_id=user.id,
            source_connection_id=connection.id,
            source_sleep_id=source_id,
            sleep_date=sleep_date,
            started_at=datetime.combine(sleep_date - timedelta(days=1), datetime.min.time(), UTC),
            ended_at=datetime.combine(sleep_date, datetime.min.time(), UTC),
            total_sleep_seconds=total_sleep_seconds,
            sleep_score=sleep_score,
            average_hrv_ms=average_hrv_ms,
            raw_data={},
        )
    )


def _add_daily_metric(
    session: Session,
    *,
    user: AppUser,
    connection: SourceConnection,
    metric_date: date,
    resting_heart_rate: int | None = None,
    hrv_ms: Decimal | None = None,
) -> None:
    session.add(
        DailyMetric(
            user_id=user.id,
            source_connection_id=connection.id,
            metric_date=metric_date,
            resting_heart_rate=resting_heart_rate,
            hrv_ms=hrv_ms,
            raw_data={},
        )
    )


def test_build_coach_metric_summary_calculates_activity_sleep_and_recovery() -> None:
    session = _create_session()
    as_of_date = date(2026, 7, 9)

    try:
        user, connection = _create_user_and_connection(session, suffix="coach")
        other_user, other_connection = _create_user_and_connection(session, suffix="other")

        _add_activity(
            session,
            user=user,
            connection=connection,
            source_id="current-1",
            activity_date=as_of_date - timedelta(days=1),
            duration_seconds=1800,
            distance_meters=Decimal("5000.00"),
            training_load=Decimal("42.50"),
            average_heart_rate=145,
        )
        _add_activity(
            session,
            user=user,
            connection=connection,
            source_id="current-2",
            activity_date=as_of_date - timedelta(days=3),
            duration_seconds=3600,
            distance_meters=Decimal("10000.00"),
            training_load=Decimal("80.00"),
            average_heart_rate=150,
        )
        _add_activity(
            session,
            user=user,
            connection=connection,
            source_id="previous-1",
            activity_date=as_of_date - timedelta(days=8),
            duration_seconds=1200,
        )
        _add_activity(
            session,
            user=other_user,
            connection=other_connection,
            source_id="other-current",
            activity_date=as_of_date,
            duration_seconds=9999,
        )

        for offset, seconds, score, hrv in [
            (0, 27000, 82, Decimal("63.00")),
            (1, 25200, 78, Decimal("61.00")),
            (2, 23400, 76, Decimal("59.00")),
        ]:
            _add_sleep(
                session,
                user=user,
                connection=connection,
                source_id=f"current-sleep-{offset}",
                sleep_date=as_of_date - timedelta(days=offset),
                total_sleep_seconds=seconds,
                sleep_score=score,
                average_hrv_ms=hrv,
            )
        for offset in [8, 9, 10]:
            _add_sleep(
                session,
                user=user,
                connection=connection,
                source_id=f"previous-sleep-{offset}",
                sleep_date=as_of_date - timedelta(days=offset),
                total_sleep_seconds=28800,
            )

        for offset, resting_hr, hrv in [
            (0, 50, Decimal("62.00")),
            (1, 52, Decimal("60.00")),
            (2, 54, Decimal("58.00")),
        ]:
            _add_daily_metric(
                session,
                user=user,
                connection=connection,
                metric_date=as_of_date - timedelta(days=offset),
                resting_heart_rate=resting_hr,
                hrv_ms=hrv,
            )
        for offset, resting_hr, hrv in [
            (8, 44, Decimal("70.00")),
            (9, 46, Decimal("68.00")),
            (10, 48, Decimal("66.00")),
        ]:
            _add_daily_metric(
                session,
                user=user,
                connection=connection,
                metric_date=as_of_date - timedelta(days=offset),
                resting_heart_rate=resting_hr,
                hrv_ms=hrv,
            )

        session.commit()

        summary = build_coach_metric_summary(
            session,
            user_id=user.id,
            as_of_date=as_of_date,
        )
    finally:
        session.close()

    assert summary.as_of_date == as_of_date
    assert summary.activity.activity_count == 2
    assert summary.activity.active_days == 2
    assert summary.activity.total_duration_seconds == 5400
    assert summary.activity.total_distance_meters == Decimal("15000.00")
    assert summary.activity.total_training_load == Decimal("122.50")
    assert summary.activity.average_heart_rate == Decimal("147.50")
    assert summary.activity.duration_trend is CoachMetricTrend.UP

    assert summary.sleep.nights_recorded == 3
    assert summary.sleep.average_sleep_seconds == 25200
    assert summary.sleep.average_sleep_score == Decimal("78.67")
    assert summary.sleep.average_sleep_hrv_ms == Decimal("61.00")
    assert summary.sleep.sleep_duration_trend is CoachMetricTrend.DOWN

    assert summary.recovery.days_recorded == 3
    assert summary.recovery.latest_resting_heart_rate == 50
    assert summary.recovery.average_resting_heart_rate == Decimal("52.00")
    assert summary.recovery.resting_heart_rate_trend is CoachMetricTrend.UP
    assert summary.recovery.latest_hrv_ms == Decimal("62.00")
    assert summary.recovery.average_hrv_ms == Decimal("60.00")
    assert summary.recovery.hrv_trend is CoachMetricTrend.DOWN

    assert summary.training_consistency.active_days == 2
    assert summary.training_consistency.days_since_last_activity == 1
    assert summary.training_consistency.longest_gap_days == 3
    assert summary.training_consistency.consistency_score == Decimal("0.29")


def test_build_coach_metric_summary_returns_empty_summary_without_data() -> None:
    session = _create_session()
    as_of_date = date(2026, 7, 9)

    try:
        user, _connection = _create_user_and_connection(session, suffix="empty")
        session.commit()

        summary = build_coach_metric_summary(
            session,
            user_id=user.id,
            as_of_date=as_of_date,
        )
    finally:
        session.close()

    assert summary.activity.activity_count == 0
    assert summary.activity.total_duration_seconds == 0
    assert summary.activity.total_distance_meters is None
    assert summary.activity.duration_trend is CoachMetricTrend.FLAT
    assert summary.sleep.nights_recorded == 0
    assert summary.sleep.average_sleep_seconds is None
    assert summary.sleep.sleep_duration_trend is CoachMetricTrend.UNKNOWN
    assert summary.recovery.days_recorded == 0
    assert summary.recovery.latest_resting_heart_rate is None
    assert summary.recovery.hrv_trend is CoachMetricTrend.UNKNOWN
    assert summary.training_consistency.active_days == 0
    assert summary.training_consistency.days_since_last_activity is None
    assert summary.training_consistency.longest_gap_days == 7
    assert summary.training_consistency.consistency_score == Decimal("0.00")
