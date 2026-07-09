from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.ai import AIProviderOutputError, validate_coach_provider_output
from app.schemas.coach import CoachInsightOutput, CoachReadinessLevel


def _valid_payload() -> dict[str, object]:
    return {
        "schema_version": "v1",
        "readiness_level": "steady",
        "title": "Keep the next session controlled",
        "summary": "Recent training is consistent and recovery signals are usable.",
        "recommendation": "Keep the next session easy and controlled.",
        "supporting_metrics": [
            {
                "name": "Active days",
                "value": 4,
                "unit": "days",
                "period": "last_7_days",
                "trend": "flat",
                "interpretation": "Training has been consistent.",
            }
        ],
        "risk_flags": [],
        "confidence": "0.72",
        "prompt_version": "daily-v1",
        "model_metadata": {
            "provider": "test",
            "model_name": "test-model",
            "response_id": "response-1",
            "generated_at": "2026-07-09T08:30:00Z",
        },
    }


def test_validate_coach_provider_output_accepts_valid_json_string() -> None:
    payload = _valid_payload()

    output = validate_coach_provider_output(
        CoachInsightOutput.model_validate(payload).model_dump_json(),
        provider_name="TestProvider",
    )

    assert output.readiness_level is CoachReadinessLevel.STEADY
    assert output.confidence == Decimal("0.72")
    assert output.model_metadata.generated_at == datetime(2026, 7, 9, 8, 30, tzinfo=UTC)


def test_validate_coach_provider_output_returns_already_valid_output() -> None:
    insight = CoachInsightOutput.model_validate(_valid_payload())

    output = validate_coach_provider_output(insight, provider_name="TestProvider")

    assert output is insight


def test_validate_coach_provider_output_rejects_invalid_json_without_echoing_output() -> None:
    with pytest.raises(AIProviderOutputError) as exc_info:
        validate_coach_provider_output(
            '{"summary": "raw health data should not be echoed"',
            provider_name="TestProvider",
        )

    assert str(exc_info.value) == "TestProvider coach output was not valid JSON"
    assert "raw health data" not in str(exc_info.value)


def test_validate_coach_provider_output_rejects_non_object_json() -> None:
    with pytest.raises(AIProviderOutputError, match="must be a JSON object"):
        validate_coach_provider_output('["not", "an", "object"]', provider_name="TestProvider")


def test_validate_coach_provider_output_rejects_schema_errors_without_echoing_output() -> None:
    payload = _valid_payload()
    payload["confidence"] = "2.0"
    payload["summary"] = "raw health data should not be echoed"

    with pytest.raises(AIProviderOutputError) as exc_info:
        validate_coach_provider_output(payload, provider_name="TestProvider")

    assert str(exc_info.value) == "TestProvider coach output failed schema validation"
    assert "raw health data" not in str(exc_info.value)
