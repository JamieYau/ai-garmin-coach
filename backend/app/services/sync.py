from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.garmin.metadata import GARMIN_SOURCE_METADATA
from app.connectors.garmin.sync import (
    DEFAULT_INCREMENTAL_WINDOW_DAYS,
    MAX_INCREMENTAL_WINDOW_DAYS,
    GarminActivitySyncService,
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


class ManualSyncService:
    def __init__(self, garmin_sync_service: GarminActivitySyncService) -> None:
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
        self._ensure_no_running_sync(db, source_connection)
        start_date, end_date = self._resolve_window(source_connection, request)

        sync_run = SyncRun(
            user_id=user.id,
            source_connection_id=source_connection.id,
            status="queued",
            sync_type="manual",
            window_start=self._window_start_datetime(start_date),
            window_end=self._window_end_datetime(end_date),
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
            results = self._run_garmin_sync(db, sync_request)
        except ValueError:
            db.rollback()
            sync_run = self._reload_sync_run(db, sync_run.id)
            mark_sync_run_failed(
                sync_run,
                error_code="manual_sync_invalid_connection",
                error_message="Manual sync could not use the configured source connection.",
            )
            db.commit()
            db.refresh(sync_run)
            return sync_run
        except Exception:
            db.rollback()
            sync_run = self._reload_sync_run(db, sync_run.id)
            mark_sync_run_failed(
                sync_run,
                error_code="manual_sync_failed",
                error_message="Manual sync failed before the connector completed.",
            )
            db.commit()
            raise

        sync_run = self._reload_sync_run(db, sync_run.id)

        failed_result = next(
            (result for result in results if result.status is SyncStatus.FAILED),
            None,
        )
        if failed_result is not None:
            if sync_run.status != "failed":
                mark_sync_run_failed(
                    sync_run,
                    error_code=failed_result.error_code or "manual_sync_failed",
                    error_message=failed_result.error_message
                    or "Manual sync failed before the connector completed.",
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

    def _run_garmin_sync(
        self,
        db: Session,
        request: BackfillSyncRequest,
    ) -> tuple[SyncResult, ...]:
        results = []
        sync_steps = (
            self._garmin_sync_service.sync_backfill_activities,
            self._garmin_sync_service.sync_backfill_daily_metrics_and_sleep,
            self._garmin_sync_service.sync_backfill_biometrics,
        )
        for sync_step in sync_steps:
            result = sync_step(db, request)
            results.append(result)
            if result.status is SyncStatus.FAILED:
                break
        return tuple(results)

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

    def _ensure_no_running_sync(self, db: Session, source_connection: SourceConnection) -> None:
        running_sync = db.scalar(
            select(SyncRun).where(
                SyncRun.source_connection_id == source_connection.id,
                SyncRun.status.in_(("queued", "running")),
            )
        )
        if running_sync is not None:
            raise SyncAlreadyRunningError("A sync is already queued or running")

    def _resolve_window(
        self,
        source_connection: SourceConnection,
        request: ManualSyncRequest,
    ) -> tuple[date, date]:
        if request.start_date is not None and request.end_date is not None:
            start_date = request.start_date
            end_date = request.end_date
        else:
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
            start_date = since.date()
            end_date = until.date()

        requested_days = (end_date - start_date).days + 1
        if requested_days > MAX_INCREMENTAL_WINDOW_DAYS:
            raise ManualSyncWindowError(
                f"Manual sync windows are limited to {MAX_INCREMENTAL_WINDOW_DAYS} days."
            )
        return start_date, end_date

    def _window_start_datetime(self, value: date) -> datetime:
        return datetime.combine(value, datetime.min.time(), tzinfo=UTC)

    def _window_end_datetime(self, value: date) -> datetime:
        return datetime.combine(value, datetime.max.time(), tzinfo=UTC)

    def _reload_sync_run(self, db: Session, sync_run_id: uuid.UUID) -> SyncRun:
        sync_run = db.get(SyncRun, sync_run_id)
        if sync_run is None:
            raise RuntimeError("Sync run disappeared during manual sync")
        return sync_run
