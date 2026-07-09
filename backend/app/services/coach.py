from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from json import dumps
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import AIProviderError, CoachProvider, CoachProviderRequest, get_coach_provider
from app.models import CoachInsight, SyncRun
from app.schemas.coach import CoachInsightOutput, CoachReadinessLevel
from app.services.coach_safety import (
    CoachSafetyAssessment,
    assess_coach_safety,
    validate_non_medical_coach_text,
)
from app.services.metric_summary import CoachMetricSummary, build_coach_metric_summary

COACH_DAILY_PROMPT_VERSION = "daily-v1"
COACH_DAILY_INSIGHT_TYPE = "daily_recovery"


class GeneratedCoachInsight(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric_summary: CoachMetricSummary
    safety_assessment: CoachSafetyAssessment
    insight: CoachInsightOutput


@dataclass(frozen=True)
class DailyInsightBatchResult:
    attempted: int
    generated: int
    failed: int
    skipped_sync_runs: int
    coach_insights: tuple[CoachInsight, ...]


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


def generate_and_persist_coach_insight(
    db: Session,
    *,
    user_id: uuid.UUID,
    as_of_date: date | None = None,
    user_notes: list[str] | None = None,
    provider: CoachProvider | None = None,
    prompt_version: str = COACH_DAILY_PROMPT_VERSION,
    generated_at: datetime | None = None,
    insight_type: str = COACH_DAILY_INSIGHT_TYPE,
    source_sync_run: SyncRun | None = None,
) -> CoachInsight:
    generated = generate_coach_insight(
        db,
        user_id=user_id,
        as_of_date=as_of_date,
        user_notes=user_notes,
        provider=provider,
        prompt_version=prompt_version,
        generated_at=generated_at,
    )
    return persist_generated_coach_insight(
        db,
        generated=generated,
        insight_type=insight_type,
        source_sync_run=source_sync_run,
    )


def generate_daily_insights_for_successful_syncs(
    db: Session,
    *,
    sync_runs: tuple[SyncRun, ...],
    provider: CoachProvider | None = None,
    generated_at: datetime | None = None,
) -> DailyInsightBatchResult:
    coach_insights: list[CoachInsight] = []
    attempted = 0
    failed = 0
    skipped = 0

    for sync_run in sync_runs:
        if sync_run.status != "succeeded":
            skipped += 1
            continue

        attempted += 1
        as_of_date = _sync_run_insight_date(sync_run)
        try:
            coach_insight = generate_and_persist_coach_insight(
                db,
                user_id=sync_run.user_id,
                as_of_date=as_of_date,
                provider=provider,
                generated_at=generated_at,
                source_sync_run=sync_run,
            )
            db.commit()
            db.refresh(coach_insight)
            coach_insights.append(coach_insight)
        except (AIProviderError, ValueError, ValidationError):
            db.rollback()
            failed += 1

    return DailyInsightBatchResult(
        attempted=attempted,
        generated=len(coach_insights),
        failed=failed,
        skipped_sync_runs=skipped,
        coach_insights=tuple(coach_insights),
    )


def persist_generated_coach_insight(
    db: Session,
    *,
    generated: GeneratedCoachInsight,
    insight_type: str = COACH_DAILY_INSIGHT_TYPE,
    source_sync_run: SyncRun | None = None,
) -> CoachInsight:
    user_id = generated.metric_summary.user_id
    if source_sync_run is not None and source_sync_run.user_id != user_id:
        raise ValueError("source_sync_run must belong to the generated insight user")

    insight_date = generated.metric_summary.as_of_date
    existing = db.scalar(
        select(CoachInsight).where(
            CoachInsight.user_id == user_id,
            CoachInsight.insight_date == insight_date,
            CoachInsight.insight_type == insight_type,
        )
    )
    values = _coach_insight_values(
        generated,
        insight_type=insight_type,
        source_sync_run=source_sync_run,
    )

    if existing is None:
        coach_insight = CoachInsight(**values)
        db.add(coach_insight)
    else:
        coach_insight = existing
        for field_name, value in values.items():
            setattr(coach_insight, field_name, value)

    db.flush()
    return coach_insight


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


def _coach_insight_values(
    generated: GeneratedCoachInsight,
    *,
    insight_type: str,
    source_sync_run: SyncRun | None,
) -> dict[str, Any]:
    insight = generated.insight
    return {
        "user_id": generated.metric_summary.user_id,
        "source_sync_run_id": source_sync_run.id if source_sync_run is not None else None,
        "source_sync_run": source_sync_run,
        "insight_date": generated.metric_summary.as_of_date,
        "insight_type": insight_type,
        "title": insight.title,
        "summary": insight.summary,
        "recommendation": insight.recommendation,
        "schema_version": insight.schema_version,
        "model_provider": insight.model_metadata.provider,
        "model_name": insight.model_metadata.model_name,
        "prompt_version": insight.prompt_version,
        "input_fingerprint": _input_fingerprint(generated),
        "output": insight.model_dump(mode="json"),
        "generated_at": insight.model_metadata.generated_at,
    }


def _input_fingerprint(generated: GeneratedCoachInsight) -> str:
    payload = {
        "metric_summary": generated.metric_summary.model_dump(mode="json"),
        "safety_assessment": generated.safety_assessment.model_dump(mode="json"),
        "prompt_version": generated.insight.prompt_version,
    }
    encoded = dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{sha256(encoded).hexdigest()}"


def _sync_run_insight_date(sync_run: SyncRun) -> date:
    if sync_run.window_end is not None:
        return sync_run.window_end.date()
    if sync_run.completed_at is not None:
        return sync_run.completed_at.date()
    return date.today()


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
