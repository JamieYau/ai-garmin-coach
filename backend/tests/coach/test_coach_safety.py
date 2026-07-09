from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.schemas.coach import CoachMetricTrend, CoachReadinessLevel, CoachRiskFlag
from app.services.coach_safety import (
    CoachRecommendationMode,
    CoachSafetyError,
    assess_coach_safety,
    validate_non_medical_coach_text,
)
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
    activity_duration_trend: CoachMetricTrend = CoachMetricTrend.FLAT,
    sleep_nights: int = 7,
    average_sleep_seconds: int | None = 7 * 60 * 60,
    average_sleep_score: Decimal | None = Decimal("78"),
    recovery_days: int = 7,
    resting_heart_rate_trend: CoachMetricTrend = CoachMetricTrend.FLAT,
    hrv_trend: CoachMetricTrend = CoachMetricTrend.FLAT,
) -> CoachMetricSummary:
    start_date = date(2026, 7, 3)
    end_date = date(2026, 7, 9)
    return CoachMetricSummary(
        user_id=uuid.uuid4(),
        as_of_date=end_date,
        activity=ActivitySummary(
            start_date=start_date,
            end_date=end_date,
            activity_count=activity_count,
            active_days=min(activity_count, 7),
            total_duration_seconds=activity_count * 1800,
            duration_trend=activity_duration_trend,
        ),
        sleep=SleepTrendSummary(
            start_date=start_date,
            end_date=end_date,
            nights_recorded=sleep_nights,
            average_sleep_seconds=average_sleep_seconds,
            average_sleep_score=average_sleep_score,
            sleep_duration_trend=CoachMetricTrend.FLAT,
        ),
        recovery=RecoveryTrendSummary(
            start_date=start_date,
            end_date=end_date,
            days_recorded=recovery_days,
            latest_resting_heart_rate=50,
            average_resting_heart_rate=Decimal("50.00"),
            resting_heart_rate_trend=resting_heart_rate_trend,
            latest_hrv_ms=Decimal("60.00"),
            average_hrv_ms=Decimal("60.00"),
            hrv_trend=hrv_trend,
        ),
        training_consistency=TrainingConsistencySummary(
            start_date=start_date,
            end_date=end_date,
            active_days=min(activity_count, 7),
            days_since_last_activity=1,
            longest_gap_days=2,
            consistency_score=Decimal("0.57"),
        ),
    )


def test_assess_coach_safety_allows_normal_guidance_for_healthy_summary() -> None:
    assessment = assess_coach_safety(_metric_summary())

    assert assessment.risk_flags == []
    assert assessment.recommendation_mode is CoachRecommendationMode.NORMAL
    assert assessment.max_readiness_level is CoachReadinessLevel.STRONG
    assert assessment.user_note_flags == []
    assert "Do not diagnose conditions" in " ".join(assessment.prompt_constraints)


def test_assess_coach_safety_flags_poor_recovery_and_conservative_guidance() -> None:
    assessment = assess_coach_safety(
        _metric_summary(
            activity_duration_trend=CoachMetricTrend.UP,
            average_sleep_seconds=5 * 60 * 60,
            average_sleep_score=Decimal("55"),
            resting_heart_rate_trend=CoachMetricTrend.UP,
            hrv_trend=CoachMetricTrend.DOWN,
        )
    )

    assert assessment.recommendation_mode is CoachRecommendationMode.REST_OR_EASY
    assert assessment.max_readiness_level is CoachReadinessLevel.CAUTION
    assert assessment.risk_flags == [
        CoachRiskFlag.SLEEP_DEFICIT,
        CoachRiskFlag.POOR_RECOVERY,
        CoachRiskFlag.ELEVATED_RESTING_HEART_RATE,
        CoachRiskFlag.LOW_HRV,
        CoachRiskFlag.HIGH_TRAINING_LOAD,
    ]
    assert "rest, mobility, or easy aerobic work" in " ".join(assessment.prompt_constraints)


def test_assess_coach_safety_flags_data_gap() -> None:
    assessment = assess_coach_safety(
        _metric_summary(
            activity_count=0,
            sleep_nights=2,
            average_sleep_seconds=None,
            average_sleep_score=None,
            recovery_days=2,
        )
    )

    assert CoachRiskFlag.DATA_GAP in assessment.risk_flags
    assert assessment.recommendation_mode is CoachRecommendationMode.CONSERVATIVE
    assert assessment.max_readiness_level is CoachReadinessLevel.STEADY


def test_assess_coach_safety_handles_injury_or_pain_notes() -> None:
    assessment = assess_coach_safety(
        _metric_summary(),
        user_notes=["Left calf pain after hill repeats."],
    )

    assert CoachRiskFlag.INJURY_OR_PAIN in assessment.risk_flags
    assert assessment.user_note_flags == ["injury_or_pain_language"]
    assert assessment.recommendation_mode is CoachRecommendationMode.REST_OR_EASY
    assert assessment.max_readiness_level is CoachReadinessLevel.CAUTION
    assert "seeking qualified help" in " ".join(assessment.prompt_constraints)


def test_validate_non_medical_coach_text_allows_training_language() -> None:
    validate_non_medical_coach_text(
        "Keep this aerobic and skip intensity if discomfort returns."
    )


def test_validate_non_medical_coach_text_rejects_diagnosis_language() -> None:
    with pytest.raises(CoachSafetyError, match="medical diagnosis"):
        validate_non_medical_coach_text("You have tendonitis and need a treatment plan.")
