from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.ai import AIProviderConfigurationError, AIProviderError, CoachProviderRequest
from app.ai.base import get_coach_provider
from app.ai.openai_provider import OpenAICoachProvider
from app.core.config import Settings
from app.schemas.coach import (
    CoachInsightOutput,
    CoachMetricTrend,
    CoachReadinessLevel,
    CoachRiskFlag,
)
from app.services.coach_safety import CoachRecommendationMode, CoachSafetyAssessment
from app.services.metric_summary import (
    ActivitySummary,
    CoachMetricSummary,
    RecoveryTrendSummary,
    SleepTrendSummary,
    TrainingConsistencySummary,
)


class _FakeParsedResponse:
    def __init__(self, *, output_parsed: CoachInsightOutput | None, response_id: str = "resp_123"):
        self.id = response_id
        self.output_parsed = output_parsed


class _FakeResponses:
    def __init__(self, parsed: CoachInsightOutput | None):
        self.parsed = parsed
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> _FakeParsedResponse:
        self.calls.append(kwargs)
        return _FakeParsedResponse(output_parsed=self.parsed)


class _FakeOpenAIClient:
    def __init__(self, parsed: CoachInsightOutput | None):
        self.responses = _FakeResponses(parsed)


def _metric_summary() -> CoachMetricSummary:
    start_date = date(2026, 7, 3)
    end_date = date(2026, 7, 9)
    return CoachMetricSummary(
        user_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        as_of_date=end_date,
        activity=ActivitySummary(
            start_date=start_date,
            end_date=end_date,
            activity_count=4,
            active_days=4,
            total_duration_seconds=7200,
            total_training_load=Decimal("120.00"),
            average_heart_rate=Decimal("145.00"),
            duration_trend=CoachMetricTrend.FLAT,
        ),
        sleep=SleepTrendSummary(
            start_date=start_date,
            end_date=end_date,
            nights_recorded=7,
            average_sleep_seconds=7 * 60 * 60,
            average_sleep_score=Decimal("78.00"),
            average_sleep_hrv_ms=Decimal("60.00"),
            sleep_duration_trend=CoachMetricTrend.FLAT,
        ),
        recovery=RecoveryTrendSummary(
            start_date=start_date,
            end_date=end_date,
            days_recorded=7,
            latest_resting_heart_rate=50,
            average_resting_heart_rate=Decimal("50.00"),
            resting_heart_rate_trend=CoachMetricTrend.FLAT,
            latest_hrv_ms=Decimal("62.00"),
            average_hrv_ms=Decimal("60.00"),
            hrv_trend=CoachMetricTrend.FLAT,
        ),
        training_consistency=TrainingConsistencySummary(
            start_date=start_date,
            end_date=end_date,
            active_days=4,
            days_since_last_activity=1,
            longest_gap_days=2,
            consistency_score=Decimal("0.57"),
        ),
    )


def _request(
    safety_assessment: CoachSafetyAssessment | None = None,
) -> CoachProviderRequest:
    return CoachProviderRequest(
        metric_summary=_metric_summary(),
        safety_assessment=safety_assessment or CoachSafetyAssessment(),
        generated_at=datetime(2026, 7, 9, 8, 30, tzinfo=UTC),
    )


def _parsed_output(
    *,
    readiness_level: CoachReadinessLevel = CoachReadinessLevel.STEADY,
    recommendation: str = "Keep the next session easy and controlled.",
    risk_flags: list[CoachRiskFlag] | None = None,
) -> CoachInsightOutput:
    return CoachInsightOutput.model_validate(
        {
            "schema_version": "v1",
            "readiness_level": readiness_level,
            "title": "Keep the next session controlled",
            "summary": "Recent training is consistent and recovery signals are usable.",
            "recommendation": recommendation,
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
            "risk_flags": risk_flags or [],
            "confidence": "0.72",
            "prompt_version": "model-provided-version",
            "model_metadata": {
                "provider": "openai",
                "model_name": "model-provided-name",
                "response_id": None,
                "generated_at": "2026-07-08T08:30:00Z",
            },
        }
    )


def test_get_coach_provider_builds_openai_provider_from_settings() -> None:
    provider = get_coach_provider(
        Settings(
            ai_provider="openai",
            openai_api_key="test-key",
            openai_model="gpt-test",
            openai_max_output_tokens=900,
        )
    )

    assert isinstance(provider, OpenAICoachProvider)
    assert provider.provider_name == "openai"
    assert provider.model_name == "gpt-test"


def test_openai_provider_requires_api_key() -> None:
    with pytest.raises(AIProviderConfigurationError, match="OPENAI_API_KEY is required"):
        get_coach_provider(Settings(ai_provider="openai", openai_api_key=None))


def test_openai_provider_uses_structured_output_parse_without_real_api_call() -> None:
    fake_client = _FakeOpenAIClient(_parsed_output())
    provider = OpenAICoachProvider(
        api_key="test-key",
        model_name="gpt-test",
        max_output_tokens=900,
        client=fake_client,
    )
    request = _request()

    insight = provider.generate_insight(request)

    assert insight.model_metadata.provider == "openai"
    assert insight.model_metadata.model_name == "gpt-test"
    assert insight.model_metadata.response_id == "resp_123"
    assert insight.model_metadata.generated_at == datetime(2026, 7, 9, 8, 30, tzinfo=UTC)
    assert insight.prompt_version == "daily-v1"

    assert len(fake_client.responses.calls) == 1
    call = fake_client.responses.calls[0]
    assert call["model"] == "gpt-test"
    assert call["text_format"] is CoachInsightOutput
    assert call["max_output_tokens"] == 900
    assert call["store"] is False
    assert "structured JSON coaching insights" in call["instructions"]
    assert "metric_summary" in call["input"]


def test_openai_provider_caps_readiness_and_replaces_risk_flags_from_safety() -> None:
    fake_client = _FakeOpenAIClient(
        _parsed_output(
            readiness_level=CoachReadinessLevel.STRONG,
            risk_flags=[],
        )
    )
    provider = OpenAICoachProvider(
        api_key="test-key",
        model_name="gpt-test",
        max_output_tokens=900,
        client=fake_client,
    )
    request = _request(
        CoachSafetyAssessment(
            risk_flags=[CoachRiskFlag.POOR_RECOVERY],
            recommendation_mode=CoachRecommendationMode.REST_OR_EASY,
            max_readiness_level=CoachReadinessLevel.CAUTION,
        )
    )

    insight = provider.generate_insight(request)

    assert insight.readiness_level is CoachReadinessLevel.CAUTION
    assert insight.risk_flags == [CoachRiskFlag.POOR_RECOVERY]


def test_openai_provider_rejects_missing_parsed_output() -> None:
    provider = OpenAICoachProvider(
        api_key="test-key",
        model_name="gpt-test",
        max_output_tokens=900,
        client=_FakeOpenAIClient(None),
    )

    with pytest.raises(AIProviderError, match="did not include parsed coach output"):
        provider.generate_insight(_request())


def test_openai_provider_rejects_medical_language_after_parsing() -> None:
    provider = OpenAICoachProvider(
        api_key="test-key",
        model_name="gpt-test",
        max_output_tokens=900,
        client=_FakeOpenAIClient(
            _parsed_output(recommendation="You have tendonitis and need a treatment plan.")
        ),
    )

    with pytest.raises(AIProviderError, match="failed safety validation"):
        provider.generate_insight(_request())
