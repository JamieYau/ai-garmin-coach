from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai import CoachProvider
from app.models import SyncRun
from app.services.coach import DailyInsightBatchResult, generate_daily_insights_for_successful_syncs


@dataclass(frozen=True)
class DailyInsightJobResult:
    attempted: int
    generated: int
    failed: int
    skipped_sync_runs: int
    coach_insight_ids: tuple[uuid.UUID, ...]

    @classmethod
    def from_batch(cls, batch: DailyInsightBatchResult) -> DailyInsightJobResult:
        return cls(
            attempted=batch.attempted,
            generated=batch.generated,
            failed=batch.failed,
            skipped_sync_runs=batch.skipped_sync_runs,
            coach_insight_ids=tuple(insight.id for insight in batch.coach_insights),
        )


def run_daily_insight_job_for_sync_runs(
    db: Session,
    *,
    sync_runs: tuple[SyncRun, ...],
    provider: CoachProvider | None = None,
) -> DailyInsightJobResult:
    batch = generate_daily_insights_for_successful_syncs(
        db,
        sync_runs=sync_runs,
        provider=provider,
    )
    return DailyInsightJobResult.from_batch(batch)
