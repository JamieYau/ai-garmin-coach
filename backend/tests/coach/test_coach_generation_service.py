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
)
from app.schemas.coach import (
    CoachInsightOutput,
    CoachModelMetadata,
    CoachReadinessLevel,
    CoachRiskFlag,
)
from app.services.coach import generate_coach_insight


def _create_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _create_user_and_connection(session: Session) -> tuple[AppUser, SourceConnection]:
    user = AppUser(
        better_auth_user_id=f"better-auth-{uuid.uuid4()}",
        email="coach-service@example.com",
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
