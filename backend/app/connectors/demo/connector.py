from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from app.connectors.demo.metadata import DEMO_SOURCE_METADATA
from app.schemas.connectors import (
    BackfillSyncRequest,
    ConnectionSetupRequest,
    ConnectionSetupResult,
    ConnectorRecordType,
    CredentialValidationRequest,
    CredentialValidationResult,
    IncrementalSyncRequest,
    NormalizationResult,
    NormalizedRecord,
    ProviderPayload,
    SyncResult,
    SyncStatus,
)


class DemoConnector:
    source = DEMO_SOURCE_METADATA.source

    def __init__(self, *, seed: str = "ai-garmin-coach-demo") -> None:
        self.seed = seed

    async def setup_connection(self, request: ConnectionSetupRequest) -> ConnectionSetupResult:
        return ConnectionSetupResult(
            source=self.source,
            provider_subject_id=f"demo-{request.user_id}",
            display_name="Demo Athlete",
            metadata={"seed": self.seed, "credentials_required": False},
        )

    async def validate_credentials(
        self,
        request: CredentialValidationRequest,
    ) -> CredentialValidationResult:
        if self._should_fail(request.metadata):
            return CredentialValidationResult(
                is_valid=False,
                requires_reauth=False,
                message="Demo connector failure requested by metadata.",
            )
        return CredentialValidationResult(is_valid=True)

    async def sync_incremental(self, request: IncrementalSyncRequest) -> SyncResult:
        if self._should_fail({}):
            return self._failed_sync_result(
                source_connection_id=request.source_connection_id,
                sync_run_id=request.sync_run_id,
            )

        until = request.until or datetime(2026, 7, 5, 12, tzinfo=UTC)
        since = request.since or until - timedelta(days=6)
        start_date = since.date()
        end_date = until.date()
        return self._sync_range(
            source_connection_id=request.source_connection_id,
            sync_run_id=request.sync_run_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def sync_backfill(self, request: BackfillSyncRequest) -> SyncResult:
        if self._should_fail({}):
            return self._failed_sync_result(
                source_connection_id=request.source_connection_id,
                sync_run_id=request.sync_run_id,
            )

        return self._sync_range(
            source_connection_id=request.source_connection_id,
            sync_run_id=request.sync_run_id,
            start_date=request.start_date,
            end_date=request.end_date,
        )

    def normalize_payload(self, payload: ProviderPayload) -> NormalizationResult:
        record_type = self._record_type_for_payload(payload.object_type)
        return NormalizationResult(
            raw_payload=payload,
            records=[
                NormalizedRecord(
                    record_type=record_type,
                    source_record_id=payload.object_id,
                    data=self._normalized_data(payload),
                )
            ],
        )

    def _sync_range(
        self,
        *,
        source_connection_id: Any,
        sync_run_id: Any,
        start_date: date,
        end_date: date,
    ) -> SyncResult:
        raw_payloads = [
            payload
            for day in self._date_range(start_date, end_date)
            for payload in self._payloads_for_day(day)
        ]
        normalized_records = [
            record
            for payload in raw_payloads
            for record in self.normalize_payload(payload).records
        ]
        return SyncResult(
            source_connection_id=source_connection_id,
            sync_run_id=sync_run_id,
            raw_payloads=raw_payloads,
            normalized_records=normalized_records,
        )

    def _payloads_for_day(self, day: date) -> tuple[ProviderPayload, ...]:
        day_index = self._day_index(day)
        run_day = day_index % 3 != 0
        payloads = [
            self._daily_metric_payload(day, day_index),
            self._sleep_payload(day, day_index),
            self._biometric_payload(day, day_index),
        ]
        if run_day:
            payloads.append(self._activity_payload(day, day_index))
        return tuple(payloads)

    def _activity_payload(self, day: date, day_index: int) -> ProviderPayload:
        started_at = datetime.combine(day, time(7, 15), tzinfo=UTC)
        duration_seconds = 1_800 + (day_index % 5) * 360
        distance_meters = 5_000 + (day_index % 6) * 850
        activity_id = f"demo-activity-{day.isoformat()}"
        payload = {
            "activityId": activity_id,
            "activityType": "running",
            "activityName": "Demo Morning Run",
            "startTimeGmt": started_at.isoformat(),
            "duration": duration_seconds,
            "movingDuration": duration_seconds - 45,
            "distance": distance_meters,
            "calories": 320 + (day_index % 5) * 42,
            "averageHR": 138 + (day_index % 8),
            "maxHR": 168 + (day_index % 10),
            "trainingLoad": round(52.5 + (day_index % 6) * 7.25, 2),
        }
        return self._provider_payload("activity", activity_id, started_at, payload)

    def _daily_metric_payload(self, day: date, day_index: int) -> ProviderPayload:
        observed_at = datetime.combine(day, time(23, 59), tzinfo=UTC)
        payload = {
            "calendarDate": day.isoformat(),
            "totalSteps": 8_200 + (day_index % 8) * 725,
            "totalKilocalories": 2_050 + (day_index % 6) * 95,
            "activeKilocalories": 420 + (day_index % 5) * 60,
            "floorsAscended": 5 + (day_index % 7),
            "activeSeconds": 2_400 + (day_index % 6) * 360,
            "highlyActiveSeconds": 900 + (day_index % 5) * 240,
            "restingHeartRate": 54 + (day_index % 6),
            "hrvMs": round(47.5 + (day_index % 7) * 1.8, 2),
            "stressAverage": round(31.0 + (day_index % 6) * 2.5, 2),
            "bodyBatteryMin": 22 + (day_index % 8),
            "bodyBatteryMax": 78 + (day_index % 10),
            "bodyBatteryLatest": 58 + (day_index % 12),
        }
        return self._provider_payload(
            "daily_metric",
            f"demo-daily-{day.isoformat()}",
            observed_at,
            payload,
        )

    def _sleep_payload(self, day: date, day_index: int) -> ProviderPayload:
        sleep_start = datetime.combine(day - timedelta(days=1), time(22, 45), tzinfo=UTC)
        total_sleep_seconds = 24_600 + (day_index % 5) * 900
        sleep_id = f"demo-sleep-{day.isoformat()}"
        sleep_end = sleep_start + timedelta(seconds=total_sleep_seconds)
        payload = {
            "sleepId": sleep_id,
            "calendarDate": day.isoformat(),
            "sleepStartTimestampGmt": sleep_start.isoformat(),
            "sleepEndTimestampGmt": sleep_end.isoformat(),
            "totalSleepSeconds": total_sleep_seconds,
            "deepSleepSeconds": 4_800 + (day_index % 4) * 300,
            "remSleepSeconds": 5_700 + (day_index % 4) * 420,
            "lightSleepSeconds": 12_600 + (day_index % 4) * 450,
            "awakeSeconds": 1_200 + (day_index % 4) * 180,
            "sleepScore": 72 + (day_index % 16),
            "averageSpo2": round(95.2 + (day_index % 4) * 0.3, 2),
            "averageHrvMs": round(44.5 + (day_index % 6) * 1.6, 2),
            "averageRespiration": round(13.8 + (day_index % 5) * 0.25, 2),
        }
        return self._provider_payload("sleep_session", sleep_id, sleep_start, payload)

    def _biometric_payload(self, day: date, day_index: int) -> ProviderPayload:
        sampled_at = datetime.combine(day, time(7), tzinfo=UTC)
        sample_id = f"demo-hrv-{day.isoformat()}"
        payload = {
            "sampleId": sample_id,
            "sampleType": "hrv",
            "sampledAt": sampled_at.isoformat(),
            "value": round(45.0 + (day_index % 7) * 1.75, 3),
            "unit": "ms",
            "aggregationWindowSeconds": 300,
        }
        return self._provider_payload("biometric_sample", sample_id, sampled_at, payload)

    def _provider_payload(
        self,
        object_type: str,
        object_id: str,
        observed_at: datetime,
        payload: dict[str, Any],
    ) -> ProviderPayload:
        return ProviderPayload(
            object_type=object_type,
            object_id=object_id,
            observed_at=observed_at,
            payload=payload,
            payload_hash=self._payload_hash(object_type, object_id),
        )

    def _normalized_data(self, payload: ProviderPayload) -> dict[str, Any]:
        data = payload.payload
        if payload.object_type == "activity":
            started_at = datetime.fromisoformat(str(data["startTimeGmt"]))
            return {
                "source_activity_id": payload.object_id,
                "activity_type": data["activityType"],
                "name": data["activityName"],
                "activity_date": started_at.date(),
                "started_at": started_at,
                "ended_at": started_at + timedelta(seconds=int(data["duration"])),
                "duration_seconds": data["duration"],
                "moving_duration_seconds": data["movingDuration"],
                "distance_meters": data["distance"],
                "calories": data["calories"],
                "average_heart_rate": data["averageHR"],
                "max_heart_rate": data["maxHR"],
                "training_load": data["trainingLoad"],
                "raw_data": data,
            }
        if payload.object_type == "daily_metric":
            return {
                "metric_date": date.fromisoformat(str(data["calendarDate"])),
                "steps": data["totalSteps"],
                "calories": data["totalKilocalories"],
                "active_calories": data["activeKilocalories"],
                "floors_ascended": data["floorsAscended"],
                "active_seconds": data["activeSeconds"],
                "highly_active_seconds": data["highlyActiveSeconds"],
                "resting_heart_rate": data["restingHeartRate"],
                "hrv_ms": data["hrvMs"],
                "stress_average": data["stressAverage"],
                "body_battery_min": data["bodyBatteryMin"],
                "body_battery_max": data["bodyBatteryMax"],
                "body_battery_latest": data["bodyBatteryLatest"],
                "raw_data": data,
            }
        if payload.object_type == "sleep_session":
            started_at = datetime.fromisoformat(str(data["sleepStartTimestampGmt"]))
            ended_at = datetime.fromisoformat(str(data["sleepEndTimestampGmt"]))
            return {
                "source_sleep_id": payload.object_id,
                "sleep_date": date.fromisoformat(str(data["calendarDate"])),
                "started_at": started_at,
                "ended_at": ended_at,
                "total_sleep_seconds": data["totalSleepSeconds"],
                "deep_sleep_seconds": data["deepSleepSeconds"],
                "rem_sleep_seconds": data["remSleepSeconds"],
                "light_sleep_seconds": data["lightSleepSeconds"],
                "awake_seconds": data["awakeSeconds"],
                "sleep_score": data["sleepScore"],
                "average_spo2": data["averageSpo2"],
                "average_hrv_ms": data["averageHrvMs"],
                "average_respiration": data["averageRespiration"],
                "raw_data": data,
            }
        if payload.object_type == "biometric_sample":
            return {
                "source_sample_id": payload.object_id,
                "sample_type": data["sampleType"],
                "sampled_at": datetime.fromisoformat(str(data["sampledAt"])),
                "value": data["value"],
                "unit": data["unit"],
                "aggregation_window_seconds": data["aggregationWindowSeconds"],
                "raw_data": data,
            }
        raise ValueError(f"Unsupported demo payload type: {payload.object_type}")

    def _record_type_for_payload(self, object_type: str) -> ConnectorRecordType:
        if object_type == "activity":
            return ConnectorRecordType.ACTIVITY
        if object_type == "daily_metric":
            return ConnectorRecordType.DAILY_METRIC
        if object_type == "sleep_session":
            return ConnectorRecordType.SLEEP_SESSION
        if object_type == "biometric_sample":
            return ConnectorRecordType.BIOMETRIC_SAMPLE
        raise ValueError(f"Unsupported demo payload type: {object_type}")

    def _failed_sync_result(self, *, source_connection_id: Any, sync_run_id: Any) -> SyncResult:
        return SyncResult(
            source_connection_id=source_connection_id,
            sync_run_id=sync_run_id,
            status=SyncStatus.FAILED,
            error_code="demo_sync_failed",
            error_message="Demo connector failure requested by configuration.",
        )

    def _should_fail(self, metadata: dict[str, Any]) -> bool:
        return bool(metadata.get("force_failure")) or self.seed == "force-failure"

    def _day_index(self, day: date) -> int:
        digest = hashlib.sha256(f"{self.seed}:{day.isoformat()}".encode()).hexdigest()
        return int(digest[:8], 16)

    def _payload_hash(self, object_type: str, object_id: str) -> str:
        return hashlib.sha256(f"{self.seed}:{object_type}:{object_id}".encode()).hexdigest()

    def _date_range(self, start_date: date, end_date: date) -> tuple[date, ...]:
        days = (end_date - start_date).days
        return tuple(start_date + timedelta(days=offset) for offset in range(days + 1))


demo_connector = DemoConnector()
