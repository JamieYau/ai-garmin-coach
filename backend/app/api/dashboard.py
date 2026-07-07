from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_app_user
from app.db.session import get_db
from app.models import (
    Activity,
    AppUser,
    CoachInsight,
    DailyMetric,
    SleepSession,
    SourceConnection,
    SyncRun,
)
from app.schemas.dashboard import (
    DashboardActivitySummary,
    DashboardInsightSummary,
    DashboardOverviewResponse,
    DashboardRecoverySummary,
    DashboardSleepSummary,
    DashboardSyncSummary,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _scalar_or_zero(value: int | None) -> int:
    return value if value is not None else 0


def _decimal_or_none(value: Decimal | None) -> Decimal | None:
    return value if value is not None else None


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    current_user: Annotated[AppUser, Depends(get_current_app_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DashboardOverviewResponse:
    today = datetime.now(UTC).date()
    seven_day_start = today - timedelta(days=6)

    activity_counts = db.execute(
        select(
            func.count(Activity.id),
            func.coalesce(func.sum(Activity.duration_seconds), 0),
            func.sum(Activity.distance_meters),
            func.max(Activity.activity_date),
        ).where(
            Activity.user_id == current_user.id,
            Activity.activity_date >= seven_day_start,
            Activity.activity_date <= today,
        )
    ).one()

    latest_metric = db.scalar(
        select(DailyMetric)
        .where(DailyMetric.user_id == current_user.id)
        .order_by(DailyMetric.metric_date.desc())
        .limit(1)
    )
    latest_sleep = db.scalar(
        select(SleepSession)
        .where(SleepSession.user_id == current_user.id)
        .order_by(SleepSession.sleep_date.desc())
        .limit(1)
    )
    latest_insight = db.scalar(
        select(CoachInsight)
        .where(CoachInsight.user_id == current_user.id)
        .order_by(CoachInsight.insight_date.desc(), CoachInsight.generated_at.desc())
        .limit(1)
    )
    latest_sync = db.scalar(
        select(SyncRun)
        .where(SyncRun.user_id == current_user.id)
        .order_by(SyncRun.created_at.desc())
        .limit(1)
    )

    connected_sources = db.scalar(
        select(func.count(SourceConnection.id)).where(SourceConnection.user_id == current_user.id)
    )
    active_sources = db.scalar(
        select(func.count(SourceConnection.id)).where(
            SourceConnection.user_id == current_user.id,
            SourceConnection.status == "active",
        )
    )

    return DashboardOverviewResponse(
        activity=DashboardActivitySummary(
            activity_count_7d=activity_counts[0],
            duration_seconds_7d=_scalar_or_zero(activity_counts[1]),
            distance_meters_7d=_decimal_or_none(activity_counts[2]),
            latest_activity_date=activity_counts[3],
        ),
        recovery=DashboardRecoverySummary(
            metric_date=latest_metric.metric_date if latest_metric is not None else None,
            steps=latest_metric.steps if latest_metric is not None else None,
            active_seconds=latest_metric.active_seconds if latest_metric is not None else None,
            resting_heart_rate=latest_metric.resting_heart_rate
            if latest_metric is not None
            else None,
            hrv_ms=latest_metric.hrv_ms if latest_metric is not None else None,
            body_battery_latest=latest_metric.body_battery_latest
            if latest_metric is not None
            else None,
            stress_average=latest_metric.stress_average if latest_metric is not None else None,
        ),
        sleep=DashboardSleepSummary(
            sleep_date=latest_sleep.sleep_date if latest_sleep is not None else None,
            total_sleep_seconds=(
                latest_sleep.total_sleep_seconds if latest_sleep is not None else None
            ),
            sleep_score=latest_sleep.sleep_score if latest_sleep is not None else None,
            average_hrv_ms=latest_sleep.average_hrv_ms if latest_sleep is not None else None,
        ),
        latest_insight=(
            DashboardInsightSummary(
                id=str(latest_insight.id),
                insight_date=latest_insight.insight_date,
                insight_type=latest_insight.insight_type,
                title=latest_insight.title,
                summary=latest_insight.summary,
                recommendation=latest_insight.recommendation,
                generated_at=latest_insight.generated_at,
            )
            if latest_insight is not None
            else None
        ),
        sync=DashboardSyncSummary(
            connected_sources=_scalar_or_zero(connected_sources),
            active_sources=_scalar_or_zero(active_sources),
            latest_sync_status=latest_sync.status if latest_sync is not None else None,
            latest_sync_completed_at=latest_sync.completed_at if latest_sync is not None else None,
            latest_sync_error_code=latest_sync.error_code if latest_sync is not None else None,
        ),
    )
