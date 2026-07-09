from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.orm import Session

from app.ai import AIProviderError, CoachProvider, CoachProviderRequest, get_coach_provider
from app.schemas.coach import CoachInsightOutput, CoachReadinessLevel
from app.services.coach_safety import (
    CoachSafetyAssessment,
    assess_coach_safety,
    validate_non_medical_coach_text,
)
from app.services.metric_summary import CoachMetricSummary, build_coach_metric_summary

COACH_DAILY_PROMPT_VERSION = "daily-v1"


class GeneratedCoachInsight(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric_summary: CoachMetricSummary
    safety_assessment: CoachSafetyAssessment
    insight: CoachInsightOutput


def generate_coach_insight(
    db: Session,
    *,
    user_id: uuid.UUID,
    as_of_date: date | None = None,
    user_notes: list[str] | None = None,
    provider: CoachProvider | None = None,
    prompt_version: str = COACH_DAILY_PROMPT_VERSION,
    generated_at: datetime | None = None,
) -> GeneratedCoachInsight:
    metric_summary = build_coach_metric_summary(
        db,
        user_id=user_id,
        as_of_date=as_of_date,
    )
    safety_assessment = assess_coach_safety(
        metric_summary,
        user_notes=user_notes,
    )
    request = CoachProviderRequest(
        metric_summary=metric_summary,
        safety_assessment=safety_assessment,
        prompt_version=prompt_version,
        user_notes=user_notes or [],
        generated_at=generated_at or datetime.now(UTC),
    )
    resolved_provider = provider or get_coach_provider()
    insight = resolved_provider.generate_insight(request)

    return GeneratedCoachInsight(
        metric_summary=metric_summary,
        safety_assessment=safety_assessment,
        insight=_validated_service_output(insight, request=request),
    )


def _validated_service_output(
    insight: CoachInsightOutput,
    *,
    request: CoachProviderRequest,
) -> CoachInsightOutput:
    _validate_text(insight)
    final_output = insight.model_copy(
        update={
            "risk_flags": request.safety_assessment.risk_flags,
            "readiness_level": _cap_readiness(
                insight.readiness_level,
                request.safety_assessment.max_readiness_level,
            ),
            "prompt_version": request.prompt_version,
        }
    )
    try:
        return CoachInsightOutput.model_validate(final_output.model_dump())
    except ValidationError as error:
        raise AIProviderError("coach service output failed validation") from error


def _validate_text(output: CoachInsightOutput) -> None:
    validate_non_medical_coach_text(output.title)
    validate_non_medical_coach_text(output.summary)
    validate_non_medical_coach_text(output.recommendation)
    for metric in output.supporting_metrics:
        if metric.interpretation is not None:
            validate_non_medical_coach_text(metric.interpretation)


def _cap_readiness(
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
