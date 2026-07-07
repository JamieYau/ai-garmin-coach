from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.connectors.garmin.mappers import (
    GarminActivityMapper,
    GarminBiometricMapper,
    GarminDailyMetricMapper,
    GarminSleepSessionMapper,
)
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


def test_garmin_daily_metric_mapper_normalizes_summary_payload() -> None:
    mapper = GarminDailyMetricMapper()

    result = mapper.normalize_daily_metric(
        {
            "calendarDate": "2026-07-05",
            "totalSteps": 12345,
            "totalKilocalories": 2410,
            "activeKilocalories": 610,
            "floorsAscended": 8,
            "activeSeconds": 3600,
            "highlyActiveSeconds": 1800,
            "restingHeartRate": 52,
            "hrvMs": 48.25,
            "stressAverage": 32.5,
            "bodyBatteryMin": 24,
            "bodyBatteryMax": 87,
            "bodyBatteryLatest": 62,
        }
    )

    assert result.raw_payload.object_type == "daily_metric"
    assert result.raw_payload.object_id == "2026-07-05"
    assert result.raw_payload.payload_hash is not None
    record = result.records[0]
    assert record.record_type is ConnectorRecordType.DAILY_METRIC
    assert record.source_record_id == "2026-07-05"
    assert record.data["metric_date"] == date(2026, 7, 5)
    assert record.data["steps"] == 12345
    assert record.data["calories"] == 2410
    assert record.data["active_calories"] == 610
    assert record.data["resting_heart_rate"] == 52
    assert record.data["hrv_ms"] == Decimal("48.25")
    assert record.data["stress_average"] == Decimal("32.5")
    assert record.data["body_battery_latest"] == 62


def test_garmin_sleep_session_mapper_normalizes_nested_sleep_payload() -> None:
    mapper = GarminSleepSessionMapper()

    result = mapper.normalize_sleep_session(
        {
            "dailySleepDTO": {
                "id": 555,
                "calendarDate": "2026-07-05",
                "sleepStartTimestampGMT": "2026-07-04T22:45:00Z",
                "sleepEndTimestampGMT": "2026-07-05T06:30:00Z",
                "sleepTimeSeconds": 27900,
                "deepSleepSeconds": 5100,
                "remSleepSeconds": 6900,
                "lightSleepSeconds": 13800,
                "awakeSleepSeconds": 2100,
                "averageSpo2": 96.2,
                "avgOvernightHrv": 47.5,
                "averageRespiration": 13.8,
            },
            "sleepScores": {"overall": {"value": 82}},
        }
    )

    assert result.raw_payload.object_type == "sleep_session"
    assert result.raw_payload.object_id == "555"
    assert result.raw_payload.observed_at == datetime(2026, 7, 4, 22, 45, tzinfo=UTC)
    record = result.records[0]
    assert record.record_type is ConnectorRecordType.SLEEP_SESSION
    assert record.data["source_sleep_id"] == "555"
    assert record.data["sleep_date"] == date(2026, 7, 5)
    assert record.data["started_at"] == datetime(2026, 7, 4, 22, 45, tzinfo=UTC)
    assert record.data["ended_at"] == datetime(2026, 7, 5, 6, 30, tzinfo=UTC)
    assert record.data["total_sleep_seconds"] == 27900
    assert record.data["deep_sleep_seconds"] == 5100
    assert record.data["awake_seconds"] == 2100
    assert record.data["sleep_score"] == 82
    assert record.data["average_spo2"] == Decimal("96.2")
    assert record.data["average_hrv_ms"] == Decimal("47.5")


def test_garmin_daily_and_sleep_mappers_reject_missing_dates() -> None:
    with pytest.raises(ValueError, match="daily summary"):
        GarminDailyMetricMapper().normalize_daily_metric({"totalSteps": 1000})

    with pytest.raises(ValueError, match="sleep payload"):
        GarminSleepSessionMapper().normalize_sleep_session({"dailySleepDTO": {"id": 1}})


def test_garmin_biometric_mapper_normalizes_heart_rate_samples() -> None:
    mapper = GarminBiometricMapper()

    result = mapper.normalize_heart_rates(
        {
            "calendarDate": "2026-07-05",
            "heartRateValues": [
                ["2026-07-05T07:30:00Z", 61],
                [30, 63],
                {"timestamp": "2026-07-05T07:31:00Z", "value": 64},
            ],
        },
        date(2026, 7, 5),
    )

    assert result.raw_payload.object_type == "heart_rate"
    assert result.raw_payload.object_id == "2026-07-05"
    assert len(result.records) == 3
    first = result.records[0]
    assert first.record_type is ConnectorRecordType.BIOMETRIC_SAMPLE
    assert first.data["sample_type"] == "heart_rate"
    assert first.data["sampled_at"] == datetime(2026, 7, 5, 7, 30, tzinfo=UTC)
    assert first.data["value"] == Decimal("61")
    assert first.data["unit"] == "bpm"
    assert result.records[1].data["sampled_at"] == datetime(2026, 7, 5, 0, 0, 30, tzinfo=UTC)


def test_garmin_biometric_mapper_normalizes_hrv_readings_and_summary() -> None:
    mapper = GarminBiometricMapper()

    reading_result = mapper.normalize_hrv(
        {
            "calendarDate": "2026-07-05",
            "hrvReadings": [
                {"readingTimeGmt": "2026-07-05T06:30:00Z", "hrvValue": 48.2},
                {"readingTimeGmt": "2026-07-05T06:35:00Z", "value": 49.1},
            ],
        },
        date(2026, 7, 5),
    )
    summary_result = mapper.normalize_hrv(
        {"calendarDate": "2026-07-05", "lastNightAvg": 47.8},
        date(2026, 7, 5),
    )

    assert reading_result.raw_payload.object_type == "hrv"
    assert len(reading_result.records) == 2
    assert reading_result.records[0].data["sample_type"] == "hrv"
    assert reading_result.records[0].data["value"] == Decimal("48.2")
    assert reading_result.records[0].data["unit"] == "ms"
    assert summary_result.records[0].data["sampled_at"] == datetime(
        2026,
        7,
        5,
        7,
        0,
        tzinfo=UTC,
    )
    assert summary_result.records[0].data["aggregation_window_seconds"] == 86_400
