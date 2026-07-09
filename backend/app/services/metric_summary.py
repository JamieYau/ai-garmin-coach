from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Activity, DailyMetric, SleepSession
from app.schemas.coach import CoachMetricTrend


class ActivitySummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start_date: date
    end_date: date
    activity_count: int = Field(ge=0)
    active_days: int = Field(ge=0)
    total_duration_seconds: int = Field(ge=0)
    total_distance_meters: Decimal | None = Field(default=None, ge=0)
    total_training_load: Decimal | None = Field(default=None, ge=0)
    average_heart_rate: Decimal | None = Field(default=None, ge=0)
    duration_trend: CoachMetricTrend = CoachMetricTrend.UNKNOWN


class SleepTrendSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start_date: date
    end_date: date
    nights_recorded: int = Field(ge=0)
    average_sleep_seconds: int | None = Field(default=None, ge=0)
    average_sleep_score: Decimal | None = Field(default=None, ge=0, le=100)
    average_sleep_hrv_ms: Decimal | None = Field(default=None, ge=0)
    sleep_duration_trend: CoachMetricTrend = CoachMetricTrend.UNKNOWN


class RecoveryTrendSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start_date: date
    end_date: date
    days_recorded: int = Field(ge=0)
    latest_resting_heart_rate: int | None = Field(default=None, ge=0)
    average_resting_heart_rate: Decimal | None = Field(default=None, ge=0)
    resting_heart_rate_trend: CoachMetricTrend = CoachMetricTrend.UNKNOWN
    latest_hrv_ms: Decimal | None = Field(default=None, ge=0)
    average_hrv_ms: Decimal | None = Field(default=None, ge=0)
    hrv_trend: CoachMetricTrend = CoachMetricTrend.UNKNOWN


class TrainingConsistencySummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start_date: date
    end_date: date
    active_days: int = Field(ge=0)
    days_since_last_activity: int | None = Field(default=None, ge=0)
    longest_gap_days: int = Field(ge=0)
    consistency_score: Decimal = Field(ge=0, le=1)


class CoachMetricSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: uuid.UUID
    as_of_date: date
    activity: ActivitySummary
    sleep: SleepTrendSummary
    recovery: RecoveryTrendSummary
    training_consistency: TrainingConsistencySummary


def build_coach_metric_summary(
    db: Session,
    *,
    user_id: uuid.UUID,
    as_of_date: date | None = None,
) -> CoachMetricSummary:
    summary_date = as_of_date or datetime.now(UTC).date()
    current_start = summary_date - timedelta(days=6)
    previous_start = summary_date - timedelta(days=13)
    previous_end = summary_date - timedelta(days=7)

    current_activities = _activities_for_window(db, user_id, current_start, summary_date)
    previous_activities = _activities_for_window(db, user_id, previous_start, previous_end)
    current_sleep = _sleep_for_window(db, user_id, current_start, summary_date)
    previous_sleep = _sleep_for_window(db, user_id, previous_start, previous_end)
    current_metrics = _daily_metrics_for_window(db, user_id, current_start, summary_date)
    previous_metrics = _daily_metrics_for_window(db, user_id, previous_start, previous_end)

    return CoachMetricSummary(
        user_id=user_id,
        as_of_date=summary_date,
        activity=_activity_summary(
            current_activities,
            previous_activities,
            start_date=current_start,
            end_date=summary_date,
        ),
        sleep=_sleep_summary(
            current_sleep,
            previous_sleep,
            start_date=current_start,
            end_date=summary_date,
        ),
        recovery=_recovery_summary(
            current_metrics,
            previous_metrics,
            start_date=current_start,
            end_date=summary_date,
        ),
        training_consistency=_training_consistency_summary(
            current_activities,
            start_date=current_start,
            end_date=summary_date,
        ),
    )


def _activities_for_window(
    db: Session,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[Activity]:
    return list(
        db.scalars(
            select(Activity)
            .where(
                Activity.user_id == user_id,
                Activity.activity_date >= start_date,
                Activity.activity_date <= end_date,
            )
            .order_by(Activity.activity_date.asc(), Activity.started_at.asc())
        ).all()
    )


def _sleep_for_window(
    db: Session,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[SleepSession]:
    return list(
        db.scalars(
            select(SleepSession)
            .where(
                SleepSession.user_id == user_id,
                SleepSession.sleep_date >= start_date,
                SleepSession.sleep_date <= end_date,
            )
            .order_by(SleepSession.sleep_date.asc(), SleepSession.started_at.asc())
        ).all()
    )


def _daily_metrics_for_window(
    db: Session,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[DailyMetric]:
    return list(
        db.scalars(
            select(DailyMetric)
            .where(
                DailyMetric.user_id == user_id,
                DailyMetric.metric_date >= start_date,
                DailyMetric.metric_date <= end_date,
            )
            .order_by(DailyMetric.metric_date.asc())
        ).all()
    )


def _activity_summary(
    current: list[Activity],
    previous: list[Activity],
    *,
    start_date: date,
    end_date: date,
) -> ActivitySummary:
    total_duration = sum(activity.duration_seconds for activity in current)
    previous_duration = sum(activity.duration_seconds for activity in previous)

    return ActivitySummary(
        start_date=start_date,
        end_date=end_date,
        activity_count=len(current),
        active_days=len({activity.activity_date for activity in current}),
        total_duration_seconds=total_duration,
        total_distance_meters=_sum_optional_decimals(
            [activity.distance_meters for activity in current]
        ),
        total_training_load=_sum_optional_decimals(
            [activity.training_load for activity in current]
        ),
        average_heart_rate=_average_ints(
            [activity.average_heart_rate for activity in current]
        ),
        duration_trend=_trend(
            Decimal(total_duration),
            Decimal(previous_duration),
            minimum_baseline=Decimal(600),
        ),
    )


def _sleep_summary(
    current: list[SleepSession],
    previous: list[SleepSession],
    *,
    start_date: date,
    end_date: date,
) -> SleepTrendSummary:
    current_sleep_seconds = [sleep.total_sleep_seconds for sleep in current]
    previous_sleep_seconds = [sleep.total_sleep_seconds for sleep in previous]

    return SleepTrendSummary(
        start_date=start_date,
        end_date=end_date,
        nights_recorded=len(current),
        average_sleep_seconds=_average_seconds(current_sleep_seconds),
        average_sleep_score=_average_ints([sleep.sleep_score for sleep in current]),
        average_sleep_hrv_ms=_average_decimals([sleep.average_hrv_ms for sleep in current]),
        sleep_duration_trend=_trend(
            _average_decimal_from_ints(current_sleep_seconds),
            _average_decimal_from_ints(previous_sleep_seconds),
            minimum_baseline=Decimal(1800),
        ),
    )


def _recovery_summary(
    current: list[DailyMetric],
    previous: list[DailyMetric],
    *,
    start_date: date,
    end_date: date,
) -> RecoveryTrendSummary:
    current_resting_heart_rates = [metric.resting_heart_rate for metric in current]
    previous_resting_heart_rates = [metric.resting_heart_rate for metric in previous]
    current_hrv = [metric.hrv_ms for metric in current]
    previous_hrv = [metric.hrv_ms for metric in previous]
    latest_hr_metric = next(
        (metric for metric in reversed(current) if metric.resting_heart_rate is not None),
        None,
    )
    latest_hrv_metric = next(
        (metric for metric in reversed(current) if metric.hrv_ms is not None),
        None,
    )

    return RecoveryTrendSummary(
        start_date=start_date,
        end_date=end_date,
        days_recorded=len(current),
        latest_resting_heart_rate=(
            latest_hr_metric.resting_heart_rate if latest_hr_metric is not None else None
        ),
        average_resting_heart_rate=_average_ints(current_resting_heart_rates),
        resting_heart_rate_trend=_trend(
            _average_decimal_from_ints(_not_none_ints(current_resting_heart_rates)),
            _average_decimal_from_ints(_not_none_ints(previous_resting_heart_rates)),
            minimum_baseline=Decimal(1),
        ),
        latest_hrv_ms=latest_hrv_metric.hrv_ms if latest_hrv_metric is not None else None,
        average_hrv_ms=_average_decimals(current_hrv),
        hrv_trend=_trend(
            _average_decimals(current_hrv),
            _average_decimals(previous_hrv),
            minimum_baseline=Decimal(1),
        ),
    )


def _training_consistency_summary(
    activities: list[Activity],
    *,
    start_date: date,
    end_date: date,
) -> TrainingConsistencySummary:
    active_dates = sorted({activity.activity_date for activity in activities})
    days_since_last_activity = (end_date - active_dates[-1]).days if active_dates else None

    return TrainingConsistencySummary(
        start_date=start_date,
        end_date=end_date,
        active_days=len(active_dates),
        days_since_last_activity=days_since_last_activity,
        longest_gap_days=_longest_gap_days(active_dates, start_date=start_date, end_date=end_date),
        consistency_score=(Decimal(len(active_dates)) / Decimal(7)).quantize(Decimal("0.01")),
    )


def _sum_optional_decimals(values: list[Decimal | None]) -> Decimal | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present, Decimal("0"))


def _average_ints(values: list[int | None]) -> Decimal | None:
    present = _not_none_ints(values)
    return _average_decimal_from_ints(present)


def _average_seconds(values: list[int]) -> int | None:
    if not values:
        return None
    return round(sum(values) / len(values))


def _average_decimals(values: list[Decimal | None]) -> Decimal | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return (sum(present, Decimal("0")) / Decimal(len(present))).quantize(Decimal("0.01"))


def _average_decimal_from_ints(values: list[int]) -> Decimal | None:
    if not values:
        return None
    return (Decimal(sum(values)) / Decimal(len(values))).quantize(Decimal("0.01"))


def _not_none_ints(values: list[int | None]) -> list[int]:
    return [value for value in values if value is not None]


def _trend(
    current: Decimal | None,
    previous: Decimal | None,
    *,
    minimum_baseline: Decimal,
) -> CoachMetricTrend:
    if current is None or previous is None:
        return CoachMetricTrend.UNKNOWN
    if abs(previous) < minimum_baseline:
        if abs(current) < minimum_baseline:
            return CoachMetricTrend.FLAT
        return CoachMetricTrend.UNKNOWN

    change_ratio = (current - previous) / abs(previous)
    if change_ratio >= Decimal("0.10"):
        return CoachMetricTrend.UP
    if change_ratio <= Decimal("-0.10"):
        return CoachMetricTrend.DOWN
    return CoachMetricTrend.FLAT


def _longest_gap_days(active_dates: list[date], *, start_date: date, end_date: date) -> int:
    if not active_dates:
        return (end_date - start_date).days + 1

    longest_gap = (active_dates[0] - start_date).days
    for previous, current in zip(active_dates, active_dates[1:], strict=False):
        longest_gap = max(longest_gap, (current - previous).days - 1)
    return max(longest_gap, (end_date - active_dates[-1]).days)
