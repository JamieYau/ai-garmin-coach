from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.base import Executable
from sqlalchemy.sql.elements import ColumnElement

from app.models import (
    Activity,
    AppUser,
    BiometricSample,
    CoachInsight,
    DailyMetric,
    RawObservation,
    SleepSession,
    SourceConnection,
    SyncRun,
)


class DataLifecycleError(Exception):
    pass


class SourceConnectionNotFoundError(DataLifecycleError):
    pass


class UnsupportedDataSourceError(DataLifecycleError):
    pass


@dataclass(frozen=True)
class DisconnectSourceResult:
    source: str
    status: str
    source_connection_id: uuid.UUID


@dataclass(frozen=True)
class DeleteSyncedDataResult:
    source: str | None
    activities_deleted: int
    daily_metrics_deleted: int
    sleep_sessions_deleted: int
    biometric_samples_deleted: int
    raw_observations_deleted: int
    sync_runs_deleted: int
    coach_insights_deleted: int

    @property
    def total_deleted(self) -> int:
        return (
            self.activities_deleted
            + self.daily_metrics_deleted
            + self.sleep_sessions_deleted
            + self.biometric_samples_deleted
            + self.raw_observations_deleted
            + self.sync_runs_deleted
            + self.coach_insights_deleted
        )


@dataclass(frozen=True)
class DeleteAccountDataResult:
    user_id: uuid.UUID
    deleted: bool
    synced_data: DeleteSyncedDataResult
    source_connections_deleted: int

    @property
    def total_deleted(self) -> int:
        return self.synced_data.total_deleted + self.source_connections_deleted + 1


SUPPORTED_DELETE_SOURCES = {"garmin"}


def disconnect_source(
    db: Session,
    user: AppUser,
    *,
    source: str,
) -> DisconnectSourceResult:
    if source not in SUPPORTED_DELETE_SOURCES:
        raise UnsupportedDataSourceError("Unsupported source")

    source_connection = _load_source_connection(db, user, source)
    source_connection.status = "disconnected"
    source_connection.connection_metadata = {
        "disconnected": True,
        "previous_source": source_connection.source,
    }
    db.commit()
    db.refresh(source_connection)
    return DisconnectSourceResult(
        source=source_connection.source,
        status=source_connection.status,
        source_connection_id=source_connection.id,
    )


def delete_synced_data(
    db: Session,
    user: AppUser,
    *,
    source: str | None = None,
) -> DeleteSyncedDataResult:
    if source is not None and source not in SUPPORTED_DELETE_SOURCES:
        raise UnsupportedDataSourceError("Unsupported source")

    source_connection_ids = _source_connection_ids(db, user, source=source)
    if source is not None and not source_connection_ids:
        raise SourceConnectionNotFoundError("Source connection not found")

    result = _delete_synced_records(
        db,
        user_id=user.id,
        source_connection_ids=source_connection_ids,
        source=source,
    )
    db.commit()
    return result


def delete_account_data(db: Session, user: AppUser) -> DeleteAccountDataResult:
    user_id = user.id
    synced_data = _delete_synced_records(
        db,
        user_id=user_id,
        source_connection_ids=None,
        source=None,
    )
    source_connections_deleted = _delete_count(
        db,
        delete(SourceConnection).where(SourceConnection.user_id == user_id),
    )
    _delete_count(db, delete(AppUser).where(AppUser.id == user_id))
    db.commit()
    return DeleteAccountDataResult(
        user_id=user_id,
        deleted=True,
        synced_data=synced_data,
        source_connections_deleted=source_connections_deleted,
    )


def _delete_synced_records(
    db: Session,
    *,
    user_id: uuid.UUID,
    source_connection_ids: tuple[uuid.UUID, ...] | None,
    source: str | None,
) -> DeleteSyncedDataResult:
    sync_run_ids = select(SyncRun.id).where(SyncRun.user_id == user_id)
    if source_connection_ids is not None:
        sync_run_ids = sync_run_ids.where(SyncRun.source_connection_id.in_(source_connection_ids))

    def condition(user_column: Any, source_connection_column: Any) -> ColumnElement[bool]:
        return _source_scoped_condition(
            user_column,
            source_connection_column,
            user_id=user_id,
            source_connection_ids=source_connection_ids,
        )

    coach_filter = CoachInsight.user_id == user_id
    if source_connection_ids is not None:
        coach_filter = coach_filter & CoachInsight.source_sync_run_id.in_(sync_run_ids)

    coach_insights_deleted = _delete_count(
        db,
        delete(CoachInsight).where(coach_filter),
    )
    raw_observations_deleted = _delete_count(
        db,
        delete(RawObservation).where(
            condition(RawObservation.user_id, RawObservation.source_connection_id)
        ),
    )
    activities_deleted = _delete_count(
        db,
        delete(Activity).where(condition(Activity.user_id, Activity.source_connection_id)),
    )
    daily_metrics_deleted = _delete_count(
        db,
        delete(DailyMetric).where(condition(DailyMetric.user_id, DailyMetric.source_connection_id)),
    )
    sleep_sessions_deleted = _delete_count(
        db,
        delete(SleepSession).where(
            condition(SleepSession.user_id, SleepSession.source_connection_id)
        ),
    )
    biometric_samples_deleted = _delete_count(
        db,
        delete(BiometricSample).where(
            condition(BiometricSample.user_id, BiometricSample.source_connection_id)
        ),
    )
    sync_runs_deleted = _delete_count(db, delete(SyncRun).where(SyncRun.id.in_(sync_run_ids)))

    return DeleteSyncedDataResult(
        source=source,
        activities_deleted=activities_deleted,
        daily_metrics_deleted=daily_metrics_deleted,
        sleep_sessions_deleted=sleep_sessions_deleted,
        biometric_samples_deleted=biometric_samples_deleted,
        raw_observations_deleted=raw_observations_deleted,
        sync_runs_deleted=sync_runs_deleted,
        coach_insights_deleted=coach_insights_deleted,
    )


def _source_scoped_condition(
    user_column: Any,
    source_connection_column: Any,
    *,
    user_id: uuid.UUID,
    source_connection_ids: tuple[uuid.UUID, ...] | None,
) -> ColumnElement[bool]:
    expression: ColumnElement[bool] = user_column == user_id
    if source_connection_ids is not None:
        expression = expression & source_connection_column.in_(source_connection_ids)
    return expression


def _source_connection_ids(
    db: Session,
    user: AppUser,
    *,
    source: str | None,
) -> tuple[uuid.UUID, ...] | None:
    if source is None:
        return None

    return tuple(
        db.scalars(
            select(SourceConnection.id).where(
                SourceConnection.user_id == user.id,
                SourceConnection.source == source,
            )
        )
    )


def _load_source_connection(db: Session, user: AppUser, source: str) -> SourceConnection:
    source_connection = db.scalar(
        select(SourceConnection).where(
            SourceConnection.user_id == user.id,
            SourceConnection.source == source,
        )
    )
    if source_connection is None:
        raise SourceConnectionNotFoundError("Source connection not found")
    return source_connection


def _delete_count(db: Session, statement: Executable) -> int:
    result: Any = db.execute(statement)
    return int(result.rowcount or 0)
