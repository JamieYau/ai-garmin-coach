from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.ai import CoachProvider
from app.connectors.garmin.sync import GarminActivitySyncService
from app.core.config import Settings, get_settings
from app.db.session import get_session_factory
from app.jobs.coach import DailyInsightJobResult, run_daily_insight_job_for_sync_runs
from app.services.sync import ScheduledSyncBatchResult, ScheduledSyncService


@dataclass(frozen=True)
class ScheduledSyncJobResult:
    started: int
    succeeded: int
    failed: int
    skipped: int
    sync_run_ids: tuple[uuid.UUID, ...]
    insights_attempted: int = 0
    insights_generated: int = 0
    insights_failed: int = 0
    coach_insight_ids: tuple[uuid.UUID, ...] = ()

    @classmethod
    def from_batch(
        cls,
        batch: ScheduledSyncBatchResult,
        insight_result: DailyInsightJobResult | None = None,
    ) -> ScheduledSyncJobResult:
        return cls(
            started=batch.started,
            succeeded=batch.succeeded,
            failed=batch.failed,
            skipped=batch.skipped_connections,
            sync_run_ids=tuple(sync_run.id for sync_run in batch.sync_runs),
            insights_attempted=insight_result.attempted if insight_result is not None else 0,
            insights_generated=insight_result.generated if insight_result is not None else 0,
            insights_failed=insight_result.failed if insight_result is not None else 0,
            coach_insight_ids=(
                insight_result.coach_insight_ids if insight_result is not None else ()
            ),
        )


def build_scheduled_sync_service(settings: Settings) -> ScheduledSyncService:
    if not settings.better_auth_secret:
        raise RuntimeError("Sync encryption is not configured")
    return ScheduledSyncService(
        GarminActivitySyncService(encryption_secret=settings.better_auth_secret)
    )


def run_scheduled_sync_job(
    db: Session,
    service: ScheduledSyncService,
    *,
    coach_provider: CoachProvider | None = None,
    generate_insights: bool = True,
) -> ScheduledSyncJobResult:
    sync_batch = service.run_due_syncs(db)
    insight_result = None
    if generate_insights:
        insight_result = run_daily_insight_job_for_sync_runs(
            db,
            sync_runs=sync_batch.sync_runs,
            provider=coach_provider,
        )
    return ScheduledSyncJobResult.from_batch(sync_batch, insight_result)


def run_scheduled_sync_job_once(
    *,
    session_factory: sessionmaker[Session] | None = None,
    service: ScheduledSyncService | None = None,
    coach_provider: CoachProvider | None = None,
    generate_insights: bool = True,
) -> ScheduledSyncJobResult:
    settings = get_settings()
    resolved_session_factory = session_factory or get_session_factory()
    if resolved_session_factory is None:
        raise RuntimeError("DATABASE_URL is not configured")

    resolved_service = service or build_scheduled_sync_service(settings)
    db = resolved_session_factory()
    try:
        return run_scheduled_sync_job(
            db,
            resolved_service,
            coach_provider=coach_provider,
            generate_insights=generate_insights,
        )
    finally:
        db.close()


def main() -> int:
    try:
        result = run_scheduled_sync_job_once()
    except RuntimeError as exc:
        print(f"scheduled sync failed: {exc}")
        return 1

    print(
        "scheduled sync finished: "
        f"started={result.started} "
        f"succeeded={result.succeeded} "
        f"failed={result.failed} "
        f"skipped={result.skipped} "
        f"insights_generated={result.insights_generated} "
        f"insights_failed={result.insights_failed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
