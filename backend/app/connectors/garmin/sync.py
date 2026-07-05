from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.garmin.client import GarminClient, GarminCredentials
from app.connectors.garmin.mappers import GarminActivityMapper, activity_mapper
from app.connectors.garmin.metadata import GARMIN_SOURCE_METADATA
from app.core.security import decrypt_json_payload
from app.models import Activity, RawObservation, SourceConnection, SyncRun
from app.schemas.connectors import (
    BackfillSyncRequest,
    ConnectorRecordType,
    NormalizedRecord,
    ProviderPayload,
    SyncResult,
    SyncStatus,
)


class GarminActivityClient(Protocol):
    def login(self, *, tokenstore: str | None = None) -> object: ...

    def get_activities_by_date(
        self,
        *,
        start_date: date,
        end_date: date | None = None,
        activity_type: str | None = None,
    ) -> list[dict[str, Any]]: ...


GarminActivityClientBuilder = Callable[[bool], GarminActivityClient]


def build_garmin_activity_client(is_cn: bool) -> GarminActivityClient:
    return GarminClient(
        GarminCredentials(username="", password=""),
        is_cn=is_cn,
    )


class GarminActivitySyncService:
    def __init__(
        self,
        *,
        encryption_secret: str,
        client_builder: GarminActivityClientBuilder = build_garmin_activity_client,
        mapper: GarminActivityMapper = activity_mapper,
    ) -> None:
        self._encryption_secret = encryption_secret
        self._client_builder = client_builder
        self._mapper = mapper

    def sync_backfill_activities(
        self,
        db: Session,
        request: BackfillSyncRequest,
    ) -> SyncResult:
        source_connection = self._load_source_connection(db, request)
        sync_run = self._load_sync_run(db, request)
        tokenstore = self._load_tokenstore(source_connection)
        raw_activities = self._fetch_activities(source_connection, request, tokenstore)
        raw_payloads: list[ProviderPayload] = []
        normalized_records: list[NormalizedRecord] = []
        sync_run.status = "running"
        sync_run.started_at = datetime.now(UTC)
        sync_run.window_start = datetime.combine(
            request.start_date,
            datetime.min.time(),
            tzinfo=UTC,
        )
        sync_run.window_end = datetime.combine(request.end_date, datetime.max.time(), tzinfo=UTC)

        for raw_activity in raw_activities:
            result = self._mapper.normalize_activity(raw_activity)
            raw_payloads.append(result.raw_payload)
            normalized_records.extend(result.records)
            self._upsert_raw_observation(db, request, result.raw_payload)
            for record in result.records:
                self._upsert_activity(db, request, record)

        sync_run.status = "succeeded"
        sync_run.completed_at = datetime.now(UTC)
        sync_run.records_seen = len(raw_payloads)
        sync_run.records_imported = len(normalized_records)
        sync_run.error_code = None
        sync_run.error_message = None
        db.commit()

        return SyncResult(
            source_connection_id=request.source_connection_id,
            sync_run_id=request.sync_run_id,
            status=SyncStatus.SUCCEEDED,
            raw_payloads=raw_payloads,
            normalized_records=normalized_records,
        )

    def _fetch_activities(
        self,
        source_connection: SourceConnection,
        request: BackfillSyncRequest,
        tokenstore: str,
    ) -> list[dict[str, Any]]:
        client = self._client_builder(source_connection.connection_metadata.get("region") == "cn")
        client.login(tokenstore=tokenstore)
        return client.get_activities_by_date(
            start_date=request.start_date,
            end_date=request.end_date,
        )

    def _load_source_connection(
        self,
        db: Session,
        request: BackfillSyncRequest,
    ) -> SourceConnection:
        source_connection = db.scalar(
            select(SourceConnection).where(
                SourceConnection.id == request.source_connection_id,
                SourceConnection.user_id == request.user_id,
                SourceConnection.source == GARMIN_SOURCE_METADATA.source,
            )
        )
        if source_connection is None:
            raise ValueError("Garmin source connection not found")
        return source_connection

    def _load_sync_run(self, db: Session, request: BackfillSyncRequest) -> SyncRun:
        sync_run = db.scalar(
            select(SyncRun).where(
                SyncRun.id == request.sync_run_id,
                SyncRun.user_id == request.user_id,
                SyncRun.source_connection_id == request.source_connection_id,
            )
        )
        if sync_run is None:
            raise ValueError("Sync run not found")
        return sync_run

    def _load_tokenstore(self, source_connection: SourceConnection) -> str:
        encrypted = source_connection.connection_metadata.get("session_material")
        if not isinstance(encrypted, dict):
            raise ValueError("Garmin source connection is missing session material")
        payload = decrypt_json_payload(encrypted, self._encryption_secret)
        tokenstore = payload.get("tokenstore")
        if not isinstance(tokenstore, str) or not tokenstore:
            raise ValueError("Garmin session material is missing tokenstore data")
        return tokenstore

    def _upsert_raw_observation(
        self,
        db: Session,
        request: BackfillSyncRequest,
        payload: ProviderPayload,
    ) -> RawObservation:
        raw_observation = db.scalar(
            select(RawObservation).where(
                RawObservation.source_connection_id == request.source_connection_id,
                RawObservation.provider_object_type == payload.object_type,
                RawObservation.provider_object_id == payload.object_id,
            )
        )
        if raw_observation is None:
            raw_observation = RawObservation(
                user_id=request.user_id,
                source_connection_id=request.source_connection_id,
                sync_run_id=request.sync_run_id,
                provider_object_type=payload.object_type,
                provider_object_id=payload.object_id,
            )
            db.add(raw_observation)

        raw_observation.sync_run_id = request.sync_run_id
        raw_observation.observed_at = payload.observed_at
        raw_observation.payload = payload.payload
        raw_observation.payload_hash = payload.payload_hash
        return raw_observation

    def _upsert_activity(
        self,
        db: Session,
        request: BackfillSyncRequest,
        record: NormalizedRecord,
    ) -> Activity:
        if record.record_type is not ConnectorRecordType.ACTIVITY:
            raise ValueError(f"Unsupported Garmin activity record type: {record.record_type}")

        activity = db.scalar(
            select(Activity).where(
                Activity.source_connection_id == request.source_connection_id,
                Activity.source_activity_id == record.source_record_id,
            )
        )
        if activity is None:
            activity = Activity(
                user_id=request.user_id,
                source_connection_id=request.source_connection_id,
                source_activity_id=record.source_record_id,
                activity_type=str(record.data["activity_type"]),
                activity_date=record.data["activity_date"],
                started_at=record.data["started_at"],
                duration_seconds=int(record.data["duration_seconds"]),
                raw_data=record.data["raw_data"],
            )
            db.add(activity)

        self._apply_activity_data(activity, record.data)
        return activity

    def _apply_activity_data(self, activity: Activity, data: dict[str, Any]) -> None:
        activity.activity_type = str(data["activity_type"])
        activity.name = self._optional_str(data.get("name"))
        activity.activity_date = data["activity_date"]
        activity.started_at = data["started_at"]
        activity.ended_at = data.get("ended_at")
        activity.duration_seconds = int(data["duration_seconds"])
        activity.moving_duration_seconds = self._optional_int(data.get("moving_duration_seconds"))
        activity.distance_meters = self._optional_decimal(data.get("distance_meters"))
        activity.calories = self._optional_int(data.get("calories"))
        activity.active_calories = self._optional_int(data.get("active_calories"))
        activity.average_heart_rate = self._optional_int(data.get("average_heart_rate"))
        activity.max_heart_rate = self._optional_int(data.get("max_heart_rate"))
        activity.elevation_gain_meters = self._optional_decimal(data.get("elevation_gain_meters"))
        activity.training_load = self._optional_decimal(data.get("training_load"))
        activity.raw_data = data["raw_data"]

    def _optional_str(self, value: object) -> str | None:
        if value is None:
            return None
        return str(value)

    def _optional_int(self, value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float | str | Decimal):
            return int(value)
        raise TypeError(f"Cannot coerce value to int: {value!r}")

    def _optional_decimal(self, value: object) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
