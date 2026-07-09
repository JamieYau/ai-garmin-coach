from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.garmin.metadata import GARMIN_SOURCE_METADATA
from app.connectors.garmin.sync import (
    DEFAULT_INCREMENTAL_WINDOW_DAYS,
    MAX_INCREMENTAL_WINDOW_DAYS,
)
from app.models import AppUser, SourceConnection, SyncRun
from app.schemas.connectors import BackfillSyncRequest, SyncResult, SyncStatus
from app.schemas.sync import ManualSyncRequest
from app.services.sync_runs import mark_sync_run_failed, mark_sync_run_succeeded


class ManualSyncError(Exception):
    pass


class UnsupportedSyncSourceError(ManualSyncError):
    pass


class SourceConnectionNotFoundError(ManualSyncError):
    pass


class SourceConnectionNotActiveError(ManualSyncError):
    pass


class SyncAlreadyRunningError(ManualSyncError):
    pass


class ManualSyncWindowError(ManualSyncError):
    pass


class GarminBackfillSyncService(Protocol):
    def sync_backfill_activities(
        self,
        db: Session,
        request: BackfillSyncRequest,
    ) -> SyncResult: ...

    def sync_backfill_daily_metrics_and_sleep(
        self,
        db: Session,
        request: BackfillSyncRequest,
    ) -> SyncResult: ...

    def sync_backfill_biometrics(
        self,
        db: Session,
        request: BackfillSyncRequest,
    ) -> SyncResult: ...


class ScheduledSyncBatchResult:
    def __init__(self, sync_runs: tuple[SyncRun, ...], skipped_connections: int) -> None:
        self.sync_runs = sync_runs
        self.skipped_connections = skipped_connections

    @property
    def started(self) -> int:
        return len(self.sync_runs)

    @property
    def succeeded(self) -> int:
        return sum(1 for sync_run in self.sync_runs if sync_run.status == "succeeded")

    @property
    def failed(self) -> int:
        return sum(1 for sync_run in self.sync_runs if sync_run.status == "failed")


class ManualSyncService:
    def __init__(self, garmin_sync_service: GarminBackfillSyncService) -> None:
        self._garmin_sync_service = garmin_sync_service

    def trigger_manual_sync(
        self,
        db: Session,
        user: AppUser,
        request: ManualSyncRequest,
    ) -> SyncRun:
        if request.source != GARMIN_SOURCE_METADATA.source:
            raise UnsupportedSyncSourceError("Unsupported sync source")

        source_connection = self._load_active_source_connection(db, user, request.source)
        ensure_no_running_sync(db, source_connection)
        start_date, end_date = self._resolve_window(source_connection, request)

        return execute_garmin_sync(
            db,
            garmin_sync_service=self._garmin_sync_service,
            user=user,
            source_connection=source_connection,
            sync_type="manual",
            start_date=start_date,
            end_date=end_date,
            invalid_connection_error_code="manual_sync_invalid_connection",
            unexpected_error_code="manual_sync_failed",
            reraise_unexpected=True,
        )

    def _load_active_source_connection(
        self,
        db: Session,
        user: AppUser,
        source: str,
    ) -> SourceConnection:
        source_connection = db.scalar(
            select(SourceConnection).where(
                SourceConnection.user_id == user.id,
                SourceConnection.source == source,
            )
        )
        if source_connection is None:
            raise SourceConnectionNotFoundError("Source connection not found")
        if source_connection.status != "active":
            raise SourceConnectionNotActiveError("Source connection is not active")
        return source_connection

    def _resolve_window(
        self,
        source_connection: SourceConnection,
        request: ManualSyncRequest,
    ) -> tuple[date, date]:
        if request.start_date is not None and request.end_date is not None:
            start_date = request.start_date
            end_date = request.end_date
        else:
            start_date, end_date = resolve_incremental_window(source_connection)

        requested_days = (end_date - start_date).days + 1
        if requested_days > MAX_INCREMENTAL_WINDOW_DAYS:
            raise ManualSyncWindowError(
                f"Manual sync windows are limited to {MAX_INCREMENTAL_WINDOW_DAYS} days."
            )
        return start_date, end_date


class ScheduledSyncService:
    def __init__(self, garmin_sync_service: GarminBackfillSyncService) -> None:
        self._garmin_sync_service = garmin_sync_service

    def run_due_syncs(self, db: Session, *, source: str = "garmin") -> ScheduledSyncBatchResult:
        if source != GARMIN_SOURCE_METADATA.source:
            raise UnsupportedSyncSourceError("Unsupported sync source")

        source_connections = tuple(
            db.scalars(
                select(SourceConnection)
                .where(
                    SourceConnection.source == source,
                    SourceConnection.status == "active",
                )
                .order_by(SourceConnection.created_at, SourceConnection.id)
            )
        )
        skipped_connections = 0
        sync_runs: list[SyncRun] = []
        for source_connection in source_connections:
            if has_running_sync(db, source_connection):
                skipped_connections += 1
                continue

            start_date, end_date = resolve_incremental_window(source_connection)
            sync_runs.append(
                execute_garmin_sync(
                    db,
                    garmin_sync_service=self._garmin_sync_service,
                    user=source_connection.user,
                    source_connection=source_connection,
                    sync_type="scheduled",
                    start_date=start_date,
                    end_date=end_date,
                    invalid_connection_error_code="scheduled_sync_invalid_connection",
                    unexpected_error_code="scheduled_sync_failed",
                    reraise_unexpected=False,
                )
            )

        return ScheduledSyncBatchResult(
            sync_runs=tuple(sync_runs),
            skipped_connections=skipped_connections,
        )


def execute_garmin_sync(
    db: Session,
    *,
    garmin_sync_service: GarminBackfillSyncService,
    user: AppUser,
    source_connection: SourceConnection,
    sync_type: str,
    start_date: date,
    end_date: date,
    invalid_connection_error_code: str,
    unexpected_error_code: str,
    reraise_unexpected: bool,
) -> SyncRun:
    sync_run = SyncRun(
        user_id=user.id,
        source_connection_id=source_connection.id,
        status="queued",
        sync_type=sync_type,
        window_start=window_start_datetime(start_date),
        window_end=window_end_datetime(end_date),
    )
    db.add(sync_run)
    db.commit()
    db.refresh(sync_run)

    sync_request = BackfillSyncRequest(
        user_id=user.id,
        source_connection_id=source_connection.id,
        sync_run_id=sync_run.id,
        start_date=start_date,
        end_date=end_date,
    )
    try:
        results = run_garmin_sync_steps(db, garmin_sync_service, sync_request)
    except ValueError:
        db.rollback()
        sync_run = reload_sync_run(db, sync_run.id)
        mark_sync_run_failed(
            sync_run,
            error_code=invalid_connection_error_code,
            error_message="Sync could not use the configured source connection.",
        )
        db.commit()
        db.refresh(sync_run)
        return sync_run
    except Exception:
        db.rollback()
        sync_run = reload_sync_run(db, sync_run.id)
        mark_sync_run_failed(
            sync_run,
            error_code=unexpected_error_code,
            error_message="Sync failed before the connector completed.",
        )
        db.commit()
        if reraise_unexpected:
            raise
        db.refresh(sync_run)
        return sync_run

    sync_run = reload_sync_run(db, sync_run.id)

    failed_result = next(
        (result for result in results if result.status is SyncStatus.FAILED),
        None,
    )
    if failed_result is not None:
        if sync_run.status != "failed":
            mark_sync_run_failed(
                sync_run,
                error_code=failed_result.error_code or f"{sync_type}_sync_failed",
                error_message=failed_result.error_message
                or "Sync failed before the connector completed.",
            )
            db.commit()
            db.refresh(sync_run)
        return sync_run

    mark_sync_run_succeeded(
        sync_run,
        records_seen=sum(result.raw_payload_count for result in results),
        records_imported=sum(result.normalized_record_count for result in results),
    )
    source_connection.last_sync_at = sync_run.completed_at
    db.commit()
    db.refresh(sync_run)
    return sync_run


def run_garmin_sync_steps(
    db: Session,
    garmin_sync_service: GarminBackfillSyncService,
    request: BackfillSyncRequest,
) -> tuple[SyncResult, ...]:
    results = []
    sync_steps = (
        garmin_sync_service.sync_backfill_activities,
        garmin_sync_service.sync_backfill_daily_metrics_and_sleep,
        garmin_sync_service.sync_backfill_biometrics,
    )
    for sync_step in sync_steps:
        result = sync_step(db, request)
        results.append(result)
        if result.status is SyncStatus.FAILED:
            break
    return tuple(results)


def has_running_sync(db: Session, source_connection: SourceConnection) -> bool:
    return (
        db.scalar(
            select(SyncRun).where(
                SyncRun.source_connection_id == source_connection.id,
                SyncRun.status.in_(("queued", "running")),
            )
        )
        is not None
    )


def ensure_no_running_sync(db: Session, source_connection: SourceConnection) -> None:
    if has_running_sync(db, source_connection):
        raise SyncAlreadyRunningError("A sync is already queued or running")


def resolve_incremental_window(source_connection: SourceConnection) -> tuple[date, date]:
    until = datetime.now(UTC)
    since = source_connection.last_sync_at or (
        until - timedelta(days=DEFAULT_INCREMENTAL_WINDOW_DAYS - 1)
    )
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    else:
        since = since.astimezone(UTC)
    earliest_allowed = until - timedelta(days=MAX_INCREMENTAL_WINDOW_DAYS - 1)
    if since < earliest_allowed:
        since = earliest_allowed
    return since.date(), until.date()


def window_start_datetime(value: date) -> datetime:
    return datetime.combine(value, datetime.min.time(), tzinfo=UTC)


def window_end_datetime(value: date) -> datetime:
    return datetime.combine(value, datetime.max.time(), tzinfo=UTC)


def reload_sync_run(db: Session, sync_run_id: uuid.UUID) -> SyncRun:
    sync_run = db.get(SyncRun, sync_run_id)
    if sync_run is None:
        raise RuntimeError("Sync run disappeared during sync")
    return sync_run
