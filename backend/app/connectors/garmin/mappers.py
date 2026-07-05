from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
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


activity_mapper = GarminActivityMapper()
