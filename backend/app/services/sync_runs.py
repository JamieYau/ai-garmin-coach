from __future__ import annotations

from datetime import UTC, datetime

from app.models import SyncRun


def mark_sync_run_running(
    sync_run: SyncRun,
    *,
    window_start: datetime,
    window_end: datetime,
) -> None:
    sync_run.status = "running"
    sync_run.started_at = datetime.now(UTC)
    sync_run.completed_at = None
    sync_run.window_start = window_start
    sync_run.window_end = window_end
    sync_run.error_code = None
    sync_run.error_message = None


def mark_sync_run_succeeded(
    sync_run: SyncRun,
    *,
    records_seen: int,
    records_imported: int,
) -> None:
    sync_run.status = "succeeded"
    sync_run.completed_at = datetime.now(UTC)
    sync_run.records_seen = records_seen
    sync_run.records_imported = records_imported
    sync_run.error_code = None
    sync_run.error_message = None


def mark_sync_run_failed(sync_run: SyncRun, *, error_code: str, error_message: str) -> None:
    sync_run.status = "failed"
    sync_run.completed_at = datetime.now(UTC)
    sync_run.records_seen = 0
    sync_run.records_imported = 0
    sync_run.error_code = error_code
    sync_run.error_message = error_message
