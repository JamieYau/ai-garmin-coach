from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from app.schemas.connectors import (
    ConnectorRecordType,
    NormalizationResult,
    NormalizedRecord,
    ProviderPayload,
)


class GarminActivityMapper:
    object_type = "activity"

    def normalize_activity(self, activity: dict[str, Any]) -> NormalizationResult:
        payload = self.to_provider_payload(activity)
        return NormalizationResult(
            raw_payload=payload,
            records=[
                NormalizedRecord(
                    record_type=ConnectorRecordType.ACTIVITY,
                    source_record_id=payload.object_id,
                    data=self.to_activity_data(payload),
                )
            ],
        )

    def to_provider_payload(self, activity: dict[str, Any]) -> ProviderPayload:
        object_id = self._required_string(activity, "activityId")
        started_at = self._parse_datetime(
            self._first_value(activity, "startTimeGMT", "startTimeGmt", "startTimeLocal")
        )
        return ProviderPayload(
            object_type=self.object_type,
            object_id=object_id,
            observed_at=started_at,
            payload=activity,
            payload_hash=self._payload_hash(activity),
        )

    def to_activity_data(self, payload: ProviderPayload) -> dict[str, Any]:
        activity = payload.payload
        started_at = self._parse_datetime(
            self._first_value(activity, "startTimeGMT", "startTimeGmt", "startTimeLocal")
        )
        duration_seconds = self._int_value(activity, "duration", default=0)
        return {
            "source_activity_id": payload.object_id,
            "activity_type": self._activity_type(activity),
            "name": self._optional_string(activity, "activityName"),
            "activity_date": started_at.date(),
            "started_at": started_at,
            "ended_at": self._ended_at(started_at, duration_seconds),
            "duration_seconds": duration_seconds,
            "moving_duration_seconds": self._optional_int(activity, "movingDuration"),
            "distance_meters": self._optional_decimal(activity, "distance"),
            "calories": self._optional_int(activity, "calories"),
            "active_calories": self._optional_int(activity, "activeKilocalories"),
            "average_heart_rate": self._optional_int(activity, "averageHR"),
            "max_heart_rate": self._optional_int(activity, "maxHR"),
            "elevation_gain_meters": self._optional_decimal(activity, "elevationGain"),
            "training_load": self._optional_decimal(activity, "trainingLoad"),
            "raw_data": activity,
        }

    def _activity_type(self, activity: dict[str, Any]) -> str:
        activity_type = activity.get("activityType")
        if isinstance(activity_type, dict):
            for key in ("typeKey", "typeId", "parentTypeId"):
                value = activity_type.get(key)
                if value is not None:
                    return str(value)
        if activity_type is not None:
            return str(activity_type)
        return "unknown"

    def _required_string(self, payload: dict[str, Any], key: str) -> str:
        value = payload.get(key)
        if value is None or str(value) == "":
            raise ValueError(f"Garmin activity payload missing {key}")
        return str(value)

    def _optional_string(self, payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        if value is None:
            return None
        return str(value)

    def _int_value(self, payload: dict[str, Any], key: str, *, default: int) -> int:
        value = payload.get(key)
        if value is None:
            return default
        return int(float(str(value)))

    def _optional_int(self, payload: dict[str, Any], key: str) -> int | None:
        value = payload.get(key)
        if value is None:
            return None
        return int(float(str(value)))

    def _optional_decimal(self, payload: dict[str, Any], key: str) -> Decimal | None:
        value = payload.get(key)
        if value is None:
            return None
        return Decimal(str(value))

    def _first_value(self, payload: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return value
        raise ValueError(f"Garmin activity payload missing one of: {', '.join(keys)}")

    def _parse_datetime(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            parsed = value
        else:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _ended_at(self, started_at: datetime, duration_seconds: int) -> datetime:
        return started_at + timedelta(seconds=duration_seconds)

    def _payload_hash(self, payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class GarminDailyMetricMapper:
    object_type = "daily_metric"

    def normalize_daily_metric(self, summary: dict[str, Any]) -> NormalizationResult:
        payload = self.to_provider_payload(summary)
        return NormalizationResult(
            raw_payload=payload,
            records=[
                NormalizedRecord(
                    record_type=ConnectorRecordType.DAILY_METRIC,
                    source_record_id=payload.object_id,
                    data=self.to_daily_metric_data(payload),
                )
            ],
        )

    def to_provider_payload(self, summary: dict[str, Any]) -> ProviderPayload:
        metric_date = self._parse_date(self._first_value(summary, "calendarDate", "date"))
        return ProviderPayload(
            object_type=self.object_type,
            object_id=metric_date.isoformat(),
            observed_at=datetime.combine(metric_date, datetime.max.time(), tzinfo=UTC),
            payload=summary,
            payload_hash=self._payload_hash(summary),
        )

    def to_daily_metric_data(self, payload: ProviderPayload) -> dict[str, Any]:
        summary = payload.payload
        metric_date = date.fromisoformat(payload.object_id)
        return {
            "metric_date": metric_date,
            "steps": self._optional_int(summary, "totalSteps", "steps"),
            "calories": self._optional_int(
                summary,
                "totalKilocalories",
                "totalCalories",
                "wellnessKilocalories",
                "burnedKilocalories",
            ),
            "active_calories": self._optional_int(
                summary,
                "activeKilocalories",
                "activeCalories",
            ),
            "floors_ascended": self._optional_int(summary, "floorsAscended"),
            "active_seconds": self._optional_int(summary, "activeSeconds"),
            "highly_active_seconds": self._optional_int(summary, "highlyActiveSeconds"),
            "resting_heart_rate": self._optional_int(
                summary,
                "restingHeartRate",
                "restingHR",
            ),
            "hrv_ms": self._optional_decimal(summary, "hrvMs", "lastNightAvg"),
            "stress_average": self._optional_decimal(
                summary,
                "stressAverage",
                "averageStressLevel",
            ),
            "body_battery_min": self._optional_int(summary, "bodyBatteryMin", "bodyBatteryLowest"),
            "body_battery_max": self._optional_int(summary, "bodyBatteryMax", "bodyBatteryHighest"),
            "body_battery_latest": self._optional_int(
                summary,
                "bodyBatteryLatest",
                "bodyBatteryMostRecentValue",
            ),
            "raw_data": summary,
        }

    def _first_value(self, payload: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return value
        raise ValueError(f"Garmin daily summary missing one of: {', '.join(keys)}")

    def _parse_date(self, value: Any) -> date:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        return date.fromisoformat(str(value)[:10])

    def _optional_int(self, payload: dict[str, Any], *keys: str) -> int | None:
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return int(float(str(value)))
        return None

    def _optional_decimal(self, payload: dict[str, Any], *keys: str) -> Decimal | None:
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return Decimal(str(value))
        return None

    def _payload_hash(self, payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class GarminSleepSessionMapper:
    object_type = "sleep_session"

    def normalize_sleep_session(self, sleep: dict[str, Any]) -> NormalizationResult:
        payload = self.to_provider_payload(sleep)
        return NormalizationResult(
            raw_payload=payload,
            records=[
                NormalizedRecord(
                    record_type=ConnectorRecordType.SLEEP_SESSION,
                    source_record_id=payload.object_id,
                    data=self.to_sleep_session_data(payload),
                )
            ],
        )

    def to_provider_payload(self, sleep: dict[str, Any]) -> ProviderPayload:
        sleep_data = self._sleep_data(sleep)
        sleep_date = self._parse_date(self._first_value(sleep_data, "calendarDate", "sleepDate"))
        object_id = str(
            sleep_data.get("sleepId")
            or sleep_data.get("id")
            or sleep_data.get("dailySleepId")
            or sleep_date.isoformat()
        )
        observed_at = self._parse_datetime(
            self._first_value(
                sleep_data,
                "sleepStartTimestampGMT",
                "sleepStartTimestampGmt",
                "sleepStartTimestampLocal",
            )
        )
        return ProviderPayload(
            object_type=self.object_type,
            object_id=object_id,
            observed_at=observed_at,
            payload=sleep,
            payload_hash=self._payload_hash(sleep),
        )

    def to_sleep_session_data(self, payload: ProviderPayload) -> dict[str, Any]:
        sleep = self._sleep_data(payload.payload)
        sleep_date = self._parse_date(self._first_value(sleep, "calendarDate", "sleepDate"))
        started_at = self._parse_datetime(
            self._first_value(
                sleep,
                "sleepStartTimestampGMT",
                "sleepStartTimestampGmt",
                "sleepStartTimestampLocal",
            )
        )
        ended_at = self._parse_datetime(
            self._first_value(
                sleep,
                "sleepEndTimestampGMT",
                "sleepEndTimestampGmt",
                "sleepEndTimestampLocal",
            )
        )
        return {
            "source_sleep_id": payload.object_id,
            "sleep_date": sleep_date,
            "started_at": started_at,
            "ended_at": ended_at,
            "total_sleep_seconds": self._required_int(
                sleep,
                "totalSleepSeconds",
                "sleepTimeSeconds",
                "durationInSeconds",
            ),
            "deep_sleep_seconds": self._optional_int(sleep, "deepSleepSeconds"),
            "rem_sleep_seconds": self._optional_int(sleep, "remSleepSeconds"),
            "light_sleep_seconds": self._optional_int(sleep, "lightSleepSeconds"),
            "awake_seconds": self._optional_int(sleep, "awakeSeconds", "awakeSleepSeconds"),
            "sleep_score": self._sleep_score(payload.payload),
            "average_spo2": self._optional_decimal(sleep, "averageSpo2", "avgSpO2"),
            "average_hrv_ms": self._optional_decimal(sleep, "averageHrvMs", "avgOvernightHrv"),
            "average_respiration": self._optional_decimal(
                sleep,
                "averageRespiration",
                "avgRespiration",
            ),
            "raw_data": payload.payload,
        }

    def _sleep_data(self, sleep: dict[str, Any]) -> dict[str, Any]:
        daily_sleep = sleep.get("dailySleepDTO")
        if isinstance(daily_sleep, dict):
            return daily_sleep
        return sleep

    def _sleep_score(self, sleep: dict[str, Any]) -> int | None:
        sleep_data = self._sleep_data(sleep)
        direct_score = self._optional_int(sleep_data, "sleepScore")
        if direct_score is not None:
            return direct_score
        scores = sleep.get("sleepScores")
        if isinstance(scores, dict):
            overall = scores.get("overall")
            if isinstance(overall, dict) and overall.get("value") is not None:
                return int(float(str(overall["value"])))
        return None

    def _first_value(self, payload: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return value
        raise ValueError(f"Garmin sleep payload missing one of: {', '.join(keys)}")

    def _parse_date(self, value: Any) -> date:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        return date.fromisoformat(str(value)[:10])

    def _parse_datetime(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            parsed = value
        else:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _required_int(self, payload: dict[str, Any], *keys: str) -> int:
        value = self._first_value(payload, *keys)
        return int(float(str(value)))

    def _optional_int(self, payload: dict[str, Any], *keys: str) -> int | None:
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return int(float(str(value)))
        return None

    def _optional_decimal(self, payload: dict[str, Any], *keys: str) -> Decimal | None:
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return Decimal(str(value))
        return None

    def _payload_hash(self, payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


activity_mapper = GarminActivityMapper()
daily_metric_mapper = GarminDailyMetricMapper()
sleep_session_mapper = GarminSleepSessionMapper()
