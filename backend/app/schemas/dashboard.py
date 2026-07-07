from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DashboardActivityDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    activity_type: str
    name: str | None = None
    activity_date: date
    started_at: datetime
    duration_seconds: int = Field(ge=0)
    moving_duration_seconds: int | None = Field(default=None, ge=0)
    distance_meters: Decimal | None = Field(default=None, ge=0)
    calories: int | None = Field(default=None, ge=0)
    average_heart_rate: int | None = Field(default=None, ge=0)
    training_load: Decimal | None = Field(default=None, ge=0)


class DashboardActivitySummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    activity_count_7d: int = Field(ge=0)
    duration_seconds_7d: int = Field(ge=0)
    distance_meters_7d: Decimal | None = Field(default=None, ge=0)
    latest_activity_date: date | None = None


class DashboardRecoverySummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric_date: date | None = None
    steps: int | None = Field(default=None, ge=0)
    active_seconds: int | None = Field(default=None, ge=0)
    resting_heart_rate: int | None = Field(default=None, ge=0)
    hrv_ms: Decimal | None = Field(default=None, ge=0)
    body_battery_latest: int | None = Field(default=None, ge=0)
    stress_average: Decimal | None = Field(default=None, ge=0)


class DashboardRecoveryMetricPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric_date: date
    steps: int | None = Field(default=None, ge=0)
    active_seconds: int | None = Field(default=None, ge=0)
    highly_active_seconds: int | None = Field(default=None, ge=0)
    resting_heart_rate: int | None = Field(default=None, ge=0)
    hrv_ms: Decimal | None = Field(default=None, ge=0)
    stress_average: Decimal | None = Field(default=None, ge=0)
    body_battery_min: int | None = Field(default=None, ge=0)
    body_battery_max: int | None = Field(default=None, ge=0)
    body_battery_latest: int | None = Field(default=None, ge=0)


class DashboardSleepSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sleep_date: date | None = None
    total_sleep_seconds: int | None = Field(default=None, ge=0)
    sleep_score: int | None = Field(default=None, ge=0, le=100)
    average_hrv_ms: Decimal | None = Field(default=None, ge=0)


class DashboardSleepTrendPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    sleep_date: date
    started_at: datetime
    ended_at: datetime
    total_sleep_seconds: int = Field(ge=0)
    deep_sleep_seconds: int | None = Field(default=None, ge=0)
    rem_sleep_seconds: int | None = Field(default=None, ge=0)
    light_sleep_seconds: int | None = Field(default=None, ge=0)
    awake_seconds: int | None = Field(default=None, ge=0)
    sleep_score: int | None = Field(default=None, ge=0, le=100)
    average_spo2: Decimal | None = Field(default=None, ge=0)
    average_hrv_ms: Decimal | None = Field(default=None, ge=0)
    average_respiration: Decimal | None = Field(default=None, ge=0)


class DashboardInsightSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    insight_date: date
    insight_type: str
    title: str
    summary: str
    recommendation: str | None = None
    generated_at: datetime


class DashboardInsightDetail(DashboardInsightSummary):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    model_provider: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    output: dict[str, Any]


class DashboardSyncSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    connected_sources: int = Field(ge=0)
    active_sources: int = Field(ge=0)
    latest_sync_status: str | None = None
    latest_sync_completed_at: datetime | None = None
    latest_sync_error_code: str | None = None


class DashboardOverviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    activity: DashboardActivitySummary
    recovery: DashboardRecoverySummary
    sleep: DashboardSleepSummary
    latest_insight: DashboardInsightSummary | None = None
    sync: DashboardSyncSummary


class DashboardRecentActivitiesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    activities: list[DashboardActivityDetail]


class DashboardSleepTrendResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    days: int = Field(ge=1)
    sleep_sessions: list[DashboardSleepTrendPoint]


class DashboardRecoveryMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    days: int = Field(ge=1)
    metrics: list[DashboardRecoveryMetricPoint]
