from __future__ import annotations

from decimal import Decimal

from app.ai.base import CoachProviderRequest
from app.schemas.coach import (
    CoachInsightOutput,
    CoachMetricTrend,
    CoachModelMetadata,
    CoachReadinessLevel,
    CoachRiskFlag,
    CoachSupportingMetric,
)
from app.services.coach_safety import (
    CoachRecommendationMode,
    validate_non_medical_coach_text,
)


class MockCoachProvider:
    provider_name = "mock"
    model_name = "deterministic-coach"

    def generate_insight(self, request: CoachProviderRequest) -> CoachInsightOutput:
        readiness_level = _readiness_level(request)
        title = _title(readiness_level, request)
        summary = _summary(request)
        recommendation = _recommendation(request)

        validate_non_medical_coach_text(title)
        validate_non_medical_coach_text(summary)
        validate_non_medical_coach_text(recommendation)

        return CoachInsightOutput(
            readiness_level=readiness_level,
            title=title,
            summary=summary,
            recommendation=recommendation,
            supporting_metrics=_supporting_metrics(request),
            risk_flags=request.safety_assessment.risk_flags,
            confidence=_confidence(request),
            prompt_version=request.prompt_version,
            model_metadata=CoachModelMetadata(
                provider=self.provider_name,
                model_name=self.model_name,
                response_id=f"mock-{request.metric_summary.user_id}-{request.metric_summary.as_of_date}",
                generated_at=request.generated_at,
            ),
        )


def _readiness_level(request: CoachProviderRequest) -> CoachReadinessLevel:
    safety = request.safety_assessment
    summary = request.metric_summary

    if safety.recommendation_mode is CoachRecommendationMode.REST_OR_EASY:
        candidate = CoachReadinessLevel.CAUTION
    elif safety.recommendation_mode is CoachRecommendationMode.CONSERVATIVE:
        candidate = CoachReadinessLevel.STEADY
    elif (
        summary.activity.active_days >= 3
        and summary.sleep.average_sleep_seconds is not None
        and summary.sleep.average_sleep_seconds >= 7 * 60 * 60
        and summary.recovery.hrv_trend in {CoachMetricTrend.FLAT, CoachMetricTrend.UP}
        and summary.recovery.resting_heart_rate_trend
        in {CoachMetricTrend.FLAT, CoachMetricTrend.DOWN}
    ):
        candidate = CoachReadinessLevel.STRONG
    else:
        candidate = CoachReadinessLevel.STEADY

    return _min_readiness(candidate, safety.max_readiness_level)


def _title(readiness_level: CoachReadinessLevel, request: CoachProviderRequest) -> str:
    if CoachRiskFlag.INJURY_OR_PAIN in request.safety_assessment.risk_flags:
        return "Keep training easy while symptoms settle"
    if request.safety_assessment.recommendation_mode is CoachRecommendationMode.REST_OR_EASY:
        return "Prioritize recovery today"
    if readiness_level is CoachReadinessLevel.STRONG:
        return "Ready for a steady training day"
    if CoachRiskFlag.DATA_GAP in request.safety_assessment.risk_flags:
        return "Use today as a conservative check-in"
    return "Keep the next session controlled"


def _summary(request: CoachProviderRequest) -> str:
    summary = request.metric_summary
    risk_flags = request.safety_assessment.risk_flags
    pieces = [
        (
            f"Over the last 7 days you recorded {summary.activity.activity_count} "
            f"activities across {summary.activity.active_days} active days."
        )
    ]

    if summary.sleep.average_sleep_seconds is not None:
        pieces.append(f"Average sleep was {_hours(summary.sleep.average_sleep_seconds)} hours.")
    else:
        pieces.append("Recent sleep data is incomplete.")

    if summary.recovery.latest_resting_heart_rate is not None:
        pieces.append(
            "Latest resting heart rate was "
            f"{summary.recovery.latest_resting_heart_rate} bpm."
        )

    if risk_flags:
        pieces.append(f"Flags to respect: {', '.join(flag.value for flag in risk_flags)}.")

    return " ".join(pieces)


def _recommendation(request: CoachProviderRequest) -> str:
    mode = request.safety_assessment.recommendation_mode

    if CoachRiskFlag.INJURY_OR_PAIN in request.safety_assessment.risk_flags:
        return (
            "Skip hard training today. Choose rest, gentle mobility, or an easy walk, and seek "
            "qualified help if symptoms persist or worsen."
        )
    if mode is CoachRecommendationMode.REST_OR_EASY:
        return "Choose rest, mobility, or easy aerobic work only, and avoid intensity today."
    if mode is CoachRecommendationMode.CONSERVATIVE:
        return (
            "Keep the session easy to moderate, shorten it if fatigue shows up, and review the "
            "next check-in before adding intensity."
        )
    return (
        "A steady aerobic session is reasonable; keep intensity controlled and stop if recovery "
        "feels off."
    )


def _supporting_metrics(request: CoachProviderRequest) -> list[CoachSupportingMetric]:
    summary = request.metric_summary
    metrics = [
        CoachSupportingMetric(
            name="Seven-day activity duration",
            value=round(summary.activity.total_duration_seconds / 60),
            unit="minutes",
            period="last_7_days",
            trend=summary.activity.duration_trend,
            interpretation="Total recorded training time for the current summary window.",
        ),
        CoachSupportingMetric(
            name="Active days",
            value=summary.training_consistency.active_days,
            unit="days",
            period="last_7_days",
            trend=CoachMetricTrend.UNKNOWN,
            interpretation="Number of days with at least one recorded activity.",
        ),
    ]

    if summary.sleep.average_sleep_seconds is not None:
        metrics.append(
            CoachSupportingMetric(
                name="Average sleep",
                value=_hours(summary.sleep.average_sleep_seconds),
                unit="hours",
                period="last_7_days",
                trend=summary.sleep.sleep_duration_trend,
                interpretation="Average sleep duration from recorded nights.",
            )
        )

    if summary.recovery.latest_hrv_ms is not None:
        metrics.append(
            CoachSupportingMetric(
                name="Latest HRV",
                value=summary.recovery.latest_hrv_ms,
                unit="ms",
                period="latest_day",
                trend=summary.recovery.hrv_trend,
                interpretation="Recent HRV trend used as a recovery signal.",
            )
        )

    return metrics


def _confidence(request: CoachProviderRequest) -> Decimal:
    summary = request.metric_summary
    data_points = min(summary.activity.activity_count, 1)
    data_points += min(summary.sleep.nights_recorded, 7)
    data_points += min(summary.recovery.days_recorded, 7)
    confidence = Decimal("0.45") + (Decimal(data_points) * Decimal("0.03"))

    if request.safety_assessment.risk_flags:
        confidence -= Decimal("0.05")

    return max(Decimal("0.20"), min(Decimal("0.85"), confidence)).quantize(Decimal("0.01"))


def _hours(seconds: int) -> Decimal:
    return (Decimal(seconds) / Decimal(3600)).quantize(Decimal("0.1"))


def _min_readiness(
    candidate: CoachReadinessLevel,
    maximum: CoachReadinessLevel,
) -> CoachReadinessLevel:
    rank = {
        CoachReadinessLevel.POOR: 0,
        CoachReadinessLevel.CAUTION: 1,
        CoachReadinessLevel.STEADY: 2,
        CoachReadinessLevel.STRONG: 3,
    }
    return candidate if rank[candidate] <= rank[maximum] else maximum
