from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


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


class DashboardSleepSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sleep_date: date | None = None
    total_sleep_seconds: int | None = Field(default=None, ge=0)
    sleep_score: int | None = Field(default=None, ge=0, le=100)
    average_hrv_ms: Decimal | None = Field(default=None, ge=0)


class DashboardInsightSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    insight_date: date
    insight_type: str
    title: str
    summary: str
    recommendation: str | None = None
    generated_at: datetime


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
