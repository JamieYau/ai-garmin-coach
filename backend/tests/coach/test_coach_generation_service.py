from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.ai import CoachProviderRequest
from app.ai.mock import MockCoachProvider
from app.db.models import Base
from app.models import (
    Activity,
    AppUser,
    CoachInsight,
    DailyMetric,
    SleepSession,
    SourceConnection,
    SyncRun,
)
from app.schemas.coach import (
    CoachInsightOutput,
    CoachModelMetadata,
    CoachReadinessLevel,
    CoachRiskFlag,
)
from app.services.coach import generate_and_persist_coach_insight, generate_coach_insight


def _create_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _create_user_and_connection(session: Session) -> tuple[AppUser, SourceConnection]:
    user_key = uuid.uuid4()
    user = AppUser(
        better_auth_user_id=f"better-auth-{user_key}",
        email=f"coach-service-{user_key}@example.com",
        display_name="Coach Service Runner",
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


def _seed_healthy_training_data(
    session: Session,
    *,
    user: AppUser,
    connection: SourceConnection,
    as_of_date: date,
) -> None:
    for offset in [0, 2, 4, 6]:
        activity_date = as_of_date - timedelta(days=offset)
        session.add(
            Activity(
                user_id=user.id,
                source_connection_id=connection.id,
                source_activity_id=f"activity-{offset}",
                activity_type="run",
                activity_date=activity_date,
                started_at=datetime.combine(activity_date, datetime.min.time(), tzinfo=UTC),
                duration_seconds=1800,
                distance_meters=Decimal("5000.00"),
                training_load=Decimal("40.00"),
                average_heart_rate=145,
                raw_data={},
            )
        )

    for offset in range(14):
        sleep_date = as_of_date - timedelta(days=offset)
        if offset < 7:
            session.add(
                SleepSession(
                    user_id=user.id,
                    source_connection_id=connection.id,
                    source_sleep_id=f"sleep-{offset}",
                    sleep_date=sleep_date,
                    started_at=datetime.combine(
                        sleep_date - timedelta(days=1),
                        datetime.min.time(),
                        tzinfo=UTC,
                    ),
                    ended_at=datetime.combine(sleep_date, datetime.min.time(), tzinfo=UTC),
                    total_sleep_seconds=7 * 60 * 60,
                    sleep_score=80,
                    average_hrv_ms=Decimal("62.00"),
                    raw_data={},
                )
            )
        session.add(
            DailyMetric(
                user_id=user.id,
                source_connection_id=connection.id,
                metric_date=sleep_date,
                resting_heart_rate=50,
                hrv_ms=Decimal("62.00"),
                raw_data={},
            )
        )


class _TooOptimisticProvider:
    provider_name = "test"
    model_name = "too-optimistic"

    def __init__(self) -> None:
        self.request: CoachProviderRequest | None = None

    def generate_insight(self, request: CoachProviderRequest) -> CoachInsightOutput:
        self.request = request
        return CoachInsightOutput(
            readiness_level=CoachReadinessLevel.STRONG,
            title="Ready for a steady training day",
            summary="Training data is sparse, so keep this as a conservative check-in.",
            recommendation="Keep the session easy and stop if recovery feels off.",
            risk_flags=[],
            confidence=Decimal("0.50"),
            prompt_version="provider-version",
            model_metadata=CoachModelMetadata(
                provider=self.provider_name,
                model_name=self.model_name,
                response_id="test-response",
                generated_at=request.generated_at,
            ),
        )


class _StaticProvider:
    provider_name = "test"
    model_name = "static"

    def __init__(self, *, title: str) -> None:
        self._title = title

    def generate_insight(self, request: CoachProviderRequest) -> CoachInsightOutput:
        return CoachInsightOutput(
            readiness_level=CoachReadinessLevel.STEADY,
            title=self._title,
            summary="Recent training data supports a controlled day.",
            recommendation="Keep the next session easy to moderate.",
            risk_flags=request.safety_assessment.risk_flags,
            confidence=Decimal("0.60"),
            prompt_version=request.prompt_version,
            model_metadata=CoachModelMetadata(
                provider=self.provider_name,
                model_name=self.model_name,
                response_id=f"static-{self._title}",
                generated_at=request.generated_at,
            ),
        )


def _create_sync_run(
    session: Session,
    *,
    user: AppUser,
    connection: SourceConnection,
    status: str = "succeeded",
) -> SyncRun:
    sync_run = SyncRun(
        user=user,
        source_connection=connection,
        status=status,
        sync_type="scheduled",
        records_seen=3,
        records_imported=3,
    )
    session.add(sync_run)
    session.flush()
    return sync_run


def test_generate_coach_insight_composes_summary_safety_and_mock_provider() -> None:
    session = _create_session()
    as_of_date = date(2026, 7, 9)
    generated_at = datetime(2026, 7, 9, 8, 30, tzinfo=UTC)

    try:
        user, connection = _create_user_and_connection(session)
        _seed_healthy_training_data(
            session,
            user=user,
            connection=connection,
            as_of_date=as_of_date,
        )
        session.commit()

        result = generate_coach_insight(
            session,
            user_id=user.id,
            as_of_date=as_of_date,
            provider=MockCoachProvider(),
            generated_at=generated_at,
        )
        persisted_count = session.scalar(select(func.count()).select_from(CoachInsight))
    finally:
        session.close()

    assert result.metric_summary.user_id == user.id
    assert result.metric_summary.as_of_date == as_of_date
    assert result.safety_assessment.risk_flags == []
    assert result.insight.readiness_level is CoachReadinessLevel.STRONG
    assert result.insight.prompt_version == "daily-v1"
    assert result.insight.model_metadata.provider == "mock"
    assert result.insight.model_metadata.generated_at == generated_at
    assert persisted_count == 0


def test_generate_coach_insight_applies_safety_limits_after_provider_output() -> None:
    session = _create_session()
    as_of_date = date(2026, 7, 9)
    generated_at = datetime(2026, 7, 9, 8, 30, tzinfo=UTC)
    provider = _TooOptimisticProvider()

    try:
        user, _connection = _create_user_and_connection(session)
        session.commit()

        result = generate_coach_insight(
            session,
            user_id=user.id,
            as_of_date=as_of_date,
            user_notes=["Left calf pain after hill repeats."],
            provider=provider,
            prompt_version="daily-test",
            generated_at=generated_at,
        )
    finally:
        session.close()

    assert provider.request is not None
    assert provider.request.safety_assessment.risk_flags == [
        CoachRiskFlag.DATA_GAP,
        CoachRiskFlag.INJURY_OR_PAIN,
    ]
    assert provider.request.user_notes == ["Left calf pain after hill repeats."]
    assert result.insight.risk_flags == [
        CoachRiskFlag.DATA_GAP,
        CoachRiskFlag.INJURY_OR_PAIN,
    ]
    assert result.insight.readiness_level is CoachReadinessLevel.CAUTION
    assert result.insight.prompt_version == "daily-test"


def test_generate_and_persist_coach_insight_creates_row_linked_to_sync_run() -> None:
    session = _create_session()
    as_of_date = date(2026, 7, 9)
    generated_at = datetime(2026, 7, 9, 8, 30, tzinfo=UTC)

    try:
        user, connection = _create_user_and_connection(session)
        connection.provider_subject_id = "garmin-user-1"
        connection.connection_metadata = {"region": "gb"}
        _seed_healthy_training_data(
            session,
            user=user,
            connection=connection,
            as_of_date=as_of_date,
        )
        sync_run = _create_sync_run(session, user=user, connection=connection)
        session.commit()

        coach_insight = generate_and_persist_coach_insight(
            session,
            user_id=user.id,
            as_of_date=as_of_date,
            provider=MockCoachProvider(),
            generated_at=generated_at,
            source_sync_run=sync_run,
        )
        persisted_count = session.scalar(select(func.count()).select_from(CoachInsight))
        linked_source = coach_insight.source_sync_run.source_connection.source
        linked_provider_subject_id = (
            coach_insight.source_sync_run.source_connection.provider_subject_id
        )
    finally:
        session.close()

    assert persisted_count == 1
    assert coach_insight.user_id == user.id
    assert coach_insight.source_sync_run_id == sync_run.id
    assert linked_source == "garmin"
    assert linked_provider_subject_id == "garmin-user-1"
    assert coach_insight.insight_date == as_of_date
    assert coach_insight.insight_type == "daily_recovery"
    assert coach_insight.title == "Ready for a steady training day"
    assert coach_insight.model_provider == "mock"
    assert coach_insight.model_name == "deterministic-coach"
    assert coach_insight.prompt_version == "daily-v1"
    assert coach_insight.input_fingerprint is not None
    assert coach_insight.input_fingerprint.startswith("sha256:")
    assert coach_insight.output["readiness_level"] == "strong"
    assert coach_insight.generated_at == generated_at


def test_generate_and_persist_coach_insight_replaces_existing_user_date_type() -> None:
    session = _create_session()
    as_of_date = date(2026, 7, 9)
    first_generated_at = datetime(2026, 7, 9, 8, 30, tzinfo=UTC)
    second_generated_at = datetime(2026, 7, 9, 9, 45, tzinfo=UTC)

    try:
        user, connection = _create_user_and_connection(session)
        first_sync_run = _create_sync_run(session, user=user, connection=connection)
        second_sync_run = _create_sync_run(session, user=user, connection=connection)
        session.commit()

        first = generate_and_persist_coach_insight(
            session,
            user_id=user.id,
            as_of_date=as_of_date,
            provider=_StaticProvider(title="First generated insight"),
            generated_at=first_generated_at,
            source_sync_run=first_sync_run,
        )
        first_id = first.id
        first_fingerprint = first.input_fingerprint

        second = generate_and_persist_coach_insight(
            session,
            user_id=user.id,
            as_of_date=as_of_date,
            provider=_StaticProvider(title="Replacement generated insight"),
            generated_at=second_generated_at,
            source_sync_run=second_sync_run,
        )
        persisted_count = session.scalar(select(func.count()).select_from(CoachInsight))
    finally:
        session.close()

    assert persisted_count == 1
    assert second.id == first_id
    assert second.title == "Replacement generated insight"
    assert second.source_sync_run_id == second_sync_run.id
    assert second.generated_at == second_generated_at
    assert second.input_fingerprint == first_fingerprint


def test_generate_and_persist_coach_insight_rejects_sync_run_for_other_user() -> None:
    session = _create_session()
    as_of_date = date(2026, 7, 9)

    try:
        user, _connection = _create_user_and_connection(session)
        other_user, other_connection = _create_user_and_connection(session)
        other_sync_run = _create_sync_run(
            session,
            user=other_user,
            connection=other_connection,
        )
        session.commit()

        try:
            generate_and_persist_coach_insight(
                session,
                user_id=user.id,
                as_of_date=as_of_date,
                provider=_StaticProvider(title="Wrong sync run"),
                source_sync_run=other_sync_run,
            )
        except ValueError as error:
            assert "source_sync_run must belong" in str(error)
        else:
            raise AssertionError("expected source sync run ownership validation")
    finally:
        session.close()
