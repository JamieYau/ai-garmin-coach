from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.coach import (
    COACH_INSIGHT_SCHEMA_VERSION,
    CoachInsightOutput,
    CoachMetricTrend,
    CoachReadinessLevel,
    CoachRiskFlag,
)


def _valid_payload() -> dict[str, object]:
    return {
        "schema_version": COACH_INSIGHT_SCHEMA_VERSION,
        "readiness_level": "steady",
        "title": "Keep the next session easy",
        "summary": "Training consistency is solid while sleep has been slightly reduced.",
        "recommendation": "Choose an easy aerobic run or rest if fatigue is noticeable.",
        "supporting_metrics": [
            {
                "name": "Seven-day training duration",
                "value": 225,
                "unit": "minutes",
                "period": "last_7_days",
                "trend": "up",
                "interpretation": "Volume is building compared with the prior week.",
            },
            {
                "name": "Average sleep",
                "value": "7.1",
                "unit": "hours",
                "period": "last_7_days",
                "trend": "flat",
            },
        ],
        "risk_flags": ["sleep_deficit"],
        "confidence": "0.78",
        "prompt_version": "daily-v1",
        "model_metadata": {
            "provider": "mock",
            "model_name": "deterministic-coach",
            "response_id": "local-response-1",
            "generated_at": "2026-07-09T08:30:00Z",
        },
    }


def test_coach_insight_output_accepts_versioned_structured_payload() -> None:
    insight = CoachInsightOutput.model_validate(_valid_payload())

    assert insight.schema_version == "v1"
    assert insight.readiness_level is CoachReadinessLevel.STEADY
    assert insight.title == "Keep the next session easy"
    assert insight.supporting_metrics[0].trend is CoachMetricTrend.UP
    assert insight.risk_flags == [CoachRiskFlag.SLEEP_DEFICIT]
    assert insight.confidence == Decimal("0.78")
    assert insight.prompt_version == "daily-v1"
    assert insight.model_metadata.provider == "mock"
    assert insight.model_metadata.generated_at == datetime(2026, 7, 9, 8, 30, tzinfo=UTC)


def test_coach_insight_output_rejects_unknown_fields() -> None:
    payload = _valid_payload()
    payload["raw_prompt"] = "do not persist raw prompts"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CoachInsightOutput.model_validate(payload)


def test_coach_insight_output_validates_readiness_and_confidence() -> None:
    payload = _valid_payload()
    payload["readiness_level"] = "race_ready"
    payload["confidence"] = "1.20"

    with pytest.raises(ValidationError) as exc_info:
        CoachInsightOutput.model_validate(payload)

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("readiness_level",) for error in errors)
    assert any(error["loc"] == ("confidence",) for error in errors)


def test_coach_insight_output_rejects_duplicate_risk_flags() -> None:
    payload = _valid_payload()
    payload["risk_flags"] = ["sleep_deficit", "sleep_deficit"]

    with pytest.raises(ValidationError, match="risk_flags must not contain duplicates"):
        CoachInsightOutput.model_validate(payload)


def test_coach_insight_output_is_immutable() -> None:
    insight = CoachInsightOutput.model_validate(_valid_payload())

    with pytest.raises(ValidationError, match="Instance is frozen"):
        insight.title = "Changed"
