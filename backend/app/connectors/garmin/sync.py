from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.garmin.client import GarminClient, GarminCredentials
from app.connectors.garmin.mappers import (
    GarminActivityMapper,
    GarminDailyMetricMapper,
    GarminSleepSessionMapper,
    activity_mapper,
    daily_metric_mapper,
    sleep_session_mapper,
)
from app.connectors.garmin.metadata import GARMIN_SOURCE_METADATA
from app.core.security import decrypt_json_payload
from app.models import (
    Activity,
    DailyMetric,
    RawObservation,
    SleepSession,
    SourceConnection,
    SyncRun,
)
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

    def get_daily_summary(self, day: date) -> dict[str, Any]: ...

    def get_sleep_data(self, day: date) -> dict[str, Any]: ...


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
        daily_mapper: GarminDailyMetricMapper = daily_metric_mapper,
        sleep_mapper: GarminSleepSessionMapper = sleep_session_mapper,
    ) -> None:
        self._encryption_secret = encryption_secret
        self._client_builder = client_builder
        self._mapper = mapper
        self._daily_mapper = daily_mapper
        self._sleep_mapper = sleep_mapper

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

    def sync_backfill_daily_metrics_and_sleep(
        self,
        db: Session,
        request: BackfillSyncRequest,
    ) -> SyncResult:
        source_connection = self._load_source_connection(db, request)
        sync_run = self._load_sync_run(db, request)
        tokenstore = self._load_tokenstore(source_connection)
        client = self._authenticated_client(source_connection, tokenstore)
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

        for day in self._date_range(request.start_date, request.end_date):
            daily_result = self._daily_mapper.normalize_daily_metric(client.get_daily_summary(day))
            raw_payloads.append(daily_result.raw_payload)
            normalized_records.extend(daily_result.records)
            self._upsert_raw_observation(db, request, daily_result.raw_payload)
            for record in daily_result.records:
                self._upsert_daily_metric(db, request, record)

            sleep_result = self._sleep_mapper.normalize_sleep_session(client.get_sleep_data(day))
            raw_payloads.append(sleep_result.raw_payload)
            normalized_records.extend(sleep_result.records)
            self._upsert_raw_observation(db, request, sleep_result.raw_payload)
            for record in sleep_result.records:
                self._upsert_sleep_session(db, request, record)

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
        client = self._authenticated_client(source_connection, tokenstore)
        return client.get_activities_by_date(
            start_date=request.start_date,
            end_date=request.end_date,
        )

    def _authenticated_client(
        self,
        source_connection: SourceConnection,
        tokenstore: str,
    ) -> GarminActivityClient:
        client = self._client_builder(source_connection.connection_metadata.get("region") == "cn")
        client.login(tokenstore=tokenstore)
        return client

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

    def _upsert_daily_metric(
        self,
        db: Session,
        request: BackfillSyncRequest,
        record: NormalizedRecord,
    ) -> DailyMetric:
        if record.record_type is not ConnectorRecordType.DAILY_METRIC:
            raise ValueError(f"Unsupported Garmin daily metric record type: {record.record_type}")

        metric = db.scalar(
            select(DailyMetric).where(
                DailyMetric.source_connection_id == request.source_connection_id,
                DailyMetric.metric_date == record.data["metric_date"],
            )
        )
        if metric is None:
            metric = DailyMetric(
                user_id=request.user_id,
                source_connection_id=request.source_connection_id,
                metric_date=record.data["metric_date"],
                raw_data=record.data["raw_data"],
            )
            db.add(metric)

        self._apply_daily_metric_data(metric, record.data)
        return metric

    def _upsert_sleep_session(
        self,
        db: Session,
        request: BackfillSyncRequest,
        record: NormalizedRecord,
    ) -> SleepSession:
        if record.record_type is not ConnectorRecordType.SLEEP_SESSION:
            raise ValueError(f"Unsupported Garmin sleep session record type: {record.record_type}")

        sleep_session = db.scalar(
            select(SleepSession).where(
                SleepSession.source_connection_id == request.source_connection_id,
                SleepSession.source_sleep_id == record.source_record_id,
            )
        )
        if sleep_session is None:
            sleep_session = SleepSession(
                user_id=request.user_id,
                source_connection_id=request.source_connection_id,
                source_sleep_id=record.source_record_id,
                sleep_date=record.data["sleep_date"],
                started_at=record.data["started_at"],
                ended_at=record.data["ended_at"],
                total_sleep_seconds=int(record.data["total_sleep_seconds"]),
                raw_data=record.data["raw_data"],
            )
            db.add(sleep_session)

        self._apply_sleep_session_data(sleep_session, record.data)
        return sleep_session

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

    def _apply_daily_metric_data(self, metric: DailyMetric, data: dict[str, Any]) -> None:
        metric.metric_date = data["metric_date"]
        metric.steps = self._optional_int(data.get("steps"))
        metric.calories = self._optional_int(data.get("calories"))
        metric.active_calories = self._optional_int(data.get("active_calories"))
        metric.floors_ascended = self._optional_int(data.get("floors_ascended"))
        metric.active_seconds = self._optional_int(data.get("active_seconds"))
        metric.highly_active_seconds = self._optional_int(data.get("highly_active_seconds"))
        metric.resting_heart_rate = self._optional_int(data.get("resting_heart_rate"))
        metric.hrv_ms = self._optional_decimal(data.get("hrv_ms"))
        metric.stress_average = self._optional_decimal(data.get("stress_average"))
        metric.body_battery_min = self._optional_int(data.get("body_battery_min"))
        metric.body_battery_max = self._optional_int(data.get("body_battery_max"))
        metric.body_battery_latest = self._optional_int(data.get("body_battery_latest"))
        metric.raw_data = data["raw_data"]

    def _apply_sleep_session_data(self, sleep_session: SleepSession, data: dict[str, Any]) -> None:
        sleep_session.sleep_date = data["sleep_date"]
        sleep_session.started_at = data["started_at"]
        sleep_session.ended_at = data["ended_at"]
        sleep_session.total_sleep_seconds = int(data["total_sleep_seconds"])
        sleep_session.deep_sleep_seconds = self._optional_int(data.get("deep_sleep_seconds"))
        sleep_session.rem_sleep_seconds = self._optional_int(data.get("rem_sleep_seconds"))
        sleep_session.light_sleep_seconds = self._optional_int(data.get("light_sleep_seconds"))
        sleep_session.awake_seconds = self._optional_int(data.get("awake_seconds"))
        sleep_session.sleep_score = self._optional_int(data.get("sleep_score"))
        sleep_session.average_spo2 = self._optional_decimal(data.get("average_spo2"))
        sleep_session.average_hrv_ms = self._optional_decimal(data.get("average_hrv_ms"))
        sleep_session.average_respiration = self._optional_decimal(data.get("average_respiration"))
        sleep_session.raw_data = data["raw_data"]

    def _date_range(self, start_date: date, end_date: date) -> tuple[date, ...]:
        days = (end_date - start_date).days
        return tuple(start_date + timedelta(days=offset) for offset in range(days + 1))

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
