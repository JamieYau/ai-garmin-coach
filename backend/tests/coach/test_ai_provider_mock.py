from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.ai import AIProviderConfigurationError, CoachProviderRequest, get_coach_provider
from app.ai.mock import MockCoachProvider
from app.core.config import Settings
from app.schemas.coach import CoachMetricTrend, CoachReadinessLevel, CoachRiskFlag
from app.services.coach_safety import CoachRecommendationMode, CoachSafetyAssessment
from app.services.metric_summary import (
    ActivitySummary,
    CoachMetricSummary,
    RecoveryTrendSummary,
    SleepTrendSummary,
    TrainingConsistencySummary,
)


def _metric_summary(
    *,
    activity_count: int = 4,
    active_days: int = 4,
    average_sleep_seconds: int | None = 7 * 60 * 60,
    sleep_nights: int = 7,
    recovery_days: int = 7,
    hrv_trend: CoachMetricTrend = CoachMetricTrend.FLAT,
    resting_heart_rate_trend: CoachMetricTrend = CoachMetricTrend.FLAT,
) -> CoachMetricSummary:
    start_date = date(2026, 7, 3)
    end_date = date(2026, 7, 9)
    return CoachMetricSummary(
        user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        as_of_date=end_date,
        activity=ActivitySummary(
            start_date=start_date,
            end_date=end_date,
            activity_count=activity_count,
            active_days=active_days,
            total_duration_seconds=activity_count * 1800,
            total_training_load=Decimal("120.00"),
            average_heart_rate=Decimal("145.00"),
            duration_trend=CoachMetricTrend.FLAT,
        ),
        sleep=SleepTrendSummary(
            start_date=start_date,
            end_date=end_date,
            nights_recorded=sleep_nights,
            average_sleep_seconds=average_sleep_seconds,
            average_sleep_score=Decimal("78.00"),
            average_sleep_hrv_ms=Decimal("60.00"),
            sleep_duration_trend=CoachMetricTrend.FLAT,
        ),
        recovery=RecoveryTrendSummary(
            start_date=start_date,
            end_date=end_date,
            days_recorded=recovery_days,
            latest_resting_heart_rate=50,
            average_resting_heart_rate=Decimal("50.00"),
            resting_heart_rate_trend=resting_heart_rate_trend,
            latest_hrv_ms=Decimal("62.00"),
            average_hrv_ms=Decimal("60.00"),
            hrv_trend=hrv_trend,
        ),
        training_consistency=TrainingConsistencySummary(
            start_date=start_date,
            end_date=end_date,
            active_days=active_days,
            days_since_last_activity=1,
            longest_gap_days=2,
            consistency_score=Decimal("0.57"),
        ),
    )


def _request(
    *,
    metric_summary: CoachMetricSummary | None = None,
    safety_assessment: CoachSafetyAssessment | None = None,
) -> CoachProviderRequest:
    return CoachProviderRequest(
        metric_summary=metric_summary or _metric_summary(),
        safety_assessment=safety_assessment or CoachSafetyAssessment(),
        generated_at=datetime(2026, 7, 9, 8, 30, tzinfo=UTC),
    )


def test_get_coach_provider_defaults_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_PROVIDER", raising=False)

    provider = get_coach_provider()

    assert isinstance(provider, MockCoachProvider)
    assert provider.provider_name == "mock"
    assert provider.model_name == "deterministic-coach"


def test_get_coach_provider_uses_explicit_mock_settings() -> None:
    provider = get_coach_provider(Settings(ai_provider=" MoCk "))

    assert isinstance(provider, MockCoachProvider)


def test_get_coach_provider_rejects_unsupported_provider() -> None:
    with pytest.raises(AIProviderConfigurationError, match="Unsupported AI_PROVIDER: ollama"):
        get_coach_provider(Settings(ai_provider="ollama"))


def test_mock_provider_generates_valid_deterministic_coach_output() -> None:
    provider = MockCoachProvider()
    request = _request()

    first = provider.generate_insight(request)
    second = provider.generate_insight(request)

    assert first == second
    assert first.readiness_level is CoachReadinessLevel.STRONG
    assert first.title == "Ready for a steady training day"
    assert first.risk_flags == []
    assert first.confidence == Decimal("0.85")
    assert first.prompt_version == "daily-v1"
    assert first.model_metadata.provider == "mock"
    assert first.model_metadata.model_name == "deterministic-coach"
    assert first.model_metadata.generated_at == datetime(2026, 7, 9, 8, 30, tzinfo=UTC)
    assert len(first.supporting_metrics) >= 3


def test_mock_provider_respects_safety_assessment_limits() -> None:
    provider = MockCoachProvider()
    request = _request(
        metric_summary=_metric_summary(
            active_days=1,
            average_sleep_seconds=5 * 60 * 60,
            hrv_trend=CoachMetricTrend.DOWN,
            resting_heart_rate_trend=CoachMetricTrend.UP,
        ),
        safety_assessment=CoachSafetyAssessment(
            risk_flags=[
                CoachRiskFlag.SLEEP_DEFICIT,
                CoachRiskFlag.POOR_RECOVERY,
                CoachRiskFlag.LOW_HRV,
            ],
            recommendation_mode=CoachRecommendationMode.REST_OR_EASY,
            max_readiness_level=CoachReadinessLevel.CAUTION,
        ),
    )

    insight = provider.generate_insight(request)

    assert insight.readiness_level is CoachReadinessLevel.CAUTION
    assert insight.title == "Prioritize recovery today"
    assert "avoid intensity" in insight.recommendation
    assert insight.risk_flags == [
        CoachRiskFlag.SLEEP_DEFICIT,
        CoachRiskFlag.POOR_RECOVERY,
        CoachRiskFlag.LOW_HRV,
    ]
