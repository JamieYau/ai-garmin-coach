from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.demo import DemoConnector, demo_connector
from app.models import (
    Activity,
    AppUser,
    BiometricSample,
    DailyMetric,
    RawObservation,
    SleepSession,
    SourceConnection,
    SyncRun,
)
from app.schemas.connectors import (
    BackfillSyncRequest,
    ConnectionSetupRequest,
    ConnectorRecordType,
    NormalizedRecord,
)
from app.services.sync_runs import mark_sync_run_running, mark_sync_run_succeeded

DEMO_DATA_WINDOW_DAYS = 14


class DemoDataService:
    """Populate an authenticated user's dashboard with deterministic synthetic records."""

    def __init__(self, connector: DemoConnector = demo_connector) -> None:
        self._connector = connector

    async def load_dashboard_data(self, db: Session, user: AppUser) -> SyncRun:
        source_connection = await self._get_or_create_connection(db, user)
        now = datetime.now(UTC)
        start_date = (now - timedelta(days=DEMO_DATA_WINDOW_DAYS - 1)).date()
        end_date = now.date()
        window_start = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        window_end = datetime.combine(end_date, datetime.max.time(), tzinfo=UTC)
        sync_run = SyncRun(
            user_id=user.id,
            source_connection_id=source_connection.id,
            status="queued",
            sync_type="backfill",
            window_start=window_start,
            window_end=window_end,
        )
        db.add(sync_run)
        db.flush()

        mark_sync_run_running(
            sync_run,
            window_start=window_start,
            window_end=window_end,
        )
        result = await self._connector.sync_backfill(
            BackfillSyncRequest(
                user_id=user.id,
                source_connection_id=source_connection.id,
                sync_run_id=sync_run.id,
                start_date=start_date,
                end_date=end_date,
            )
        )
        if result.status.value == "failed":
            raise RuntimeError("Demo data generation failed")

        for payload in result.raw_payloads:
            self._upsert_raw_observation(db, user, source_connection, sync_run, payload)
        for record in result.normalized_records:
            self._upsert_record(db, user, source_connection, record)

        mark_sync_run_succeeded(
            sync_run,
            records_seen=result.raw_payload_count,
            records_imported=result.normalized_record_count,
        )
        source_connection.last_sync_at = sync_run.completed_at
        db.commit()
        db.refresh(sync_run)
        return sync_run

    async def _get_or_create_connection(self, db: Session, user: AppUser) -> SourceConnection:
        source_connection = db.scalar(
            select(SourceConnection).where(
                SourceConnection.user_id == user.id,
                SourceConnection.source == self._connector.source,
            )
        )
        if source_connection is not None:
            source_connection.status = "active"
            source_connection.connection_metadata = {
                "demo": True,
                "seed": self._connector.seed,
                "credentials_required": False,
            }
            return source_connection

        # The demo connector is deterministic and never sends or stores credentials.
        # Keep setup separate from persistence so every connector owns its own metadata.
        result = await self._connector.setup_connection(
            ConnectionSetupRequest(
                user_id=user.id,
                source=self._connector.source,
            )
        )
        source_connection = SourceConnection(
            user_id=user.id,
            source=result.source,
            status=result.status,
            provider_subject_id=result.provider_subject_id,
            display_name=result.display_name,
            connection_metadata={"demo": True, **result.metadata},
        )
        db.add(source_connection)
        db.flush()
        return source_connection

    def _upsert_raw_observation(
        self,
        db: Session,
        user: AppUser,
        source_connection: SourceConnection,
        sync_run: SyncRun,
        payload: Any,
    ) -> None:
        observation = db.scalar(
            select(RawObservation).where(
                RawObservation.source_connection_id == source_connection.id,
                RawObservation.provider_object_type == payload.object_type,
                RawObservation.provider_object_id == payload.object_id,
            )
        )
        values = {
            "user_id": user.id,
            "source_connection_id": source_connection.id,
            "sync_run_id": sync_run.id,
            "provider_object_type": payload.object_type,
            "provider_object_id": payload.object_id,
            "observed_at": payload.observed_at,
            "payload": payload.payload,
            "payload_hash": payload.payload_hash,
        }
        if observation is None:
            db.add(RawObservation(**values))
        else:
            for field, value in values.items():
                setattr(observation, field, value)

    def _upsert_record(
        self,
        db: Session,
        user: AppUser,
        source_connection: SourceConnection,
        record: NormalizedRecord,
    ) -> None:
        data = record.data
        common = {"user_id": user.id, "source_connection_id": source_connection.id}
        if record.record_type is ConnectorRecordType.ACTIVITY:
            self._upsert_by_source_id(
                db, Activity, "source_activity_id", record.source_record_id, common | data
            )
        elif record.record_type is ConnectorRecordType.DAILY_METRIC:
            self._upsert_by_source_id(
                db,
                DailyMetric,
                "metric_date",
                data["metric_date"],
                common | data,
            )
        elif record.record_type is ConnectorRecordType.SLEEP_SESSION:
            self._upsert_by_source_id(
                db, SleepSession, "source_sleep_id", record.source_record_id, common | data
            )
        elif record.record_type is ConnectorRecordType.BIOMETRIC_SAMPLE:
            self._upsert_by_source_id(
                db, BiometricSample, "source_sample_id", record.source_record_id, common | data
            )

    def _upsert_by_source_id(
        self,
        db: Session,
        model: type[Activity] | type[DailyMetric] | type[SleepSession] | type[BiometricSample],
        field: str,
        identifier: Any,
        values: dict[str, Any],
    ) -> None:
        record = db.scalar(
            select(model).where(
                model.source_connection_id == values["source_connection_id"],
                getattr(model, field) == identifier,
            )
        )
        if record is None:
            db.add(model(**values))
        else:
            for name, value in values.items():
                setattr(record, name, value)
