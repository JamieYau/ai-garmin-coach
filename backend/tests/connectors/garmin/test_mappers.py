from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.connectors.garmin.mappers import GarminActivityMapper
from app.schemas.connectors import ConnectorRecordType


def _garmin_activity() -> dict[str, object]:
    return {
        "activityId": 987654321,
        "activityName": "Morning Run",
        "activityType": {"typeKey": "running"},
        "startTimeGMT": "2026-07-05T07:30:00.000Z",
        "duration": 2700.0,
        "movingDuration": 2645.2,
        "distance": 10012.34,
        "calories": 642,
        "activeKilocalories": 601,
        "averageHR": 151,
        "maxHR": 176,
        "elevationGain": 88.5,
        "trainingLoad": 82.25,
    }


def test_garmin_activity_mapper_normalizes_activity_payload() -> None:
    mapper = GarminActivityMapper()

    result = mapper.normalize_activity(_garmin_activity())

    assert result.raw_payload.object_type == "activity"
    assert result.raw_payload.object_id == "987654321"
    assert result.raw_payload.observed_at == datetime(2026, 7, 5, 7, 30, tzinfo=UTC)
    assert result.raw_payload.payload_hash is not None
    assert len(result.records) == 1
    record = result.records[0]
    assert record.record_type is ConnectorRecordType.ACTIVITY
    assert record.source_record_id == "987654321"
    assert record.data["activity_type"] == "running"
    assert record.data["activity_date"] == date(2026, 7, 5)
    assert record.data["started_at"] == datetime(2026, 7, 5, 7, 30, tzinfo=UTC)
    assert record.data["ended_at"] == datetime(2026, 7, 5, 7, 30, tzinfo=UTC) + timedelta(
        seconds=2700
    )
    assert record.data["duration_seconds"] == 2700
    assert record.data["moving_duration_seconds"] == 2645
    assert record.data["distance_meters"] == Decimal("10012.34")
    assert record.data["training_load"] == Decimal("82.25")
    assert record.data["raw_data"]["activityId"] == 987654321


def test_garmin_activity_mapper_accepts_string_activity_type_and_naive_time() -> None:
    mapper = GarminActivityMapper()
    payload = _garmin_activity()
    payload["activityType"] = "cycling"
    payload["startTimeGMT"] = "2026-07-05T07:30:00"

    result = mapper.normalize_activity(payload)

    assert result.records[0].data["activity_type"] == "cycling"
    assert result.records[0].data["started_at"] == datetime(2026, 7, 5, 7, 30, tzinfo=UTC)


def test_garmin_activity_mapper_rejects_missing_identity_or_start() -> None:
    mapper = GarminActivityMapper()
    missing_id = _garmin_activity()
    del missing_id["activityId"]
    missing_start = _garmin_activity()
    del missing_start["startTimeGMT"]

    with pytest.raises(ValueError, match="activityId"):
        mapper.normalize_activity(missing_id)

    with pytest.raises(ValueError, match="startTime"):
        mapper.normalize_activity(missing_start)
