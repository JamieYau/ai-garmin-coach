from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
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
    DashboardActivityDetail,
    DashboardActivitySummary,
    DashboardInsightDetail,
    DashboardInsightSummary,
    DashboardOverviewResponse,
    DashboardRecentActivitiesResponse,
    DashboardRecoveryMetricPoint,
    DashboardRecoveryMetricsResponse,
    DashboardRecoverySummary,
    DashboardSleepSummary,
    DashboardSleepTrendPoint,
    DashboardSleepTrendResponse,
    DashboardSyncSummary,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _scalar_or_zero(value: int | None) -> int:
    return value if value is not None else 0


def _decimal_or_none(value: Decimal | None) -> Decimal | None:
    return value if value is not None else None


def _insight_summary(insight: CoachInsight) -> DashboardInsightSummary:
    return DashboardInsightSummary(
        id=str(insight.id),
        insight_date=insight.insight_date,
        insight_type=insight.insight_type,
        title=insight.title,
        summary=insight.summary,
        recommendation=insight.recommendation,
        generated_at=insight.generated_at,
    )


def _insight_detail(insight: CoachInsight) -> DashboardInsightDetail:
    return DashboardInsightDetail(
        id=str(insight.id),
        insight_date=insight.insight_date,
        insight_type=insight.insight_type,
        title=insight.title,
        summary=insight.summary,
        recommendation=insight.recommendation,
        generated_at=insight.generated_at,
        schema_version=insight.schema_version,
        model_provider=insight.model_provider,
        model_name=insight.model_name,
        prompt_version=insight.prompt_version,
        output=insight.output,
    )


def _latest_insight_for_user(db: Session, user: AppUser) -> CoachInsight | None:
    return db.scalar(
        select(CoachInsight)
        .where(CoachInsight.user_id == user.id)
        .order_by(CoachInsight.insight_date.desc(), CoachInsight.generated_at.desc())
        .limit(1)
    )


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
    latest_insight = _latest_insight_for_user(db, current_user)
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
    has_demo_data = db.scalar(
        select(func.count(SourceConnection.id)).where(
            SourceConnection.user_id == current_user.id,
            (
                (SourceConnection.source == "demo")
                | (SourceConnection.connection_metadata["demo"].as_boolean().is_(True))
            ),
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
            _insight_summary(latest_insight)
            if latest_insight is not None
            else None
        ),
        sync=DashboardSyncSummary(
            connected_sources=_scalar_or_zero(connected_sources),
            active_sources=_scalar_or_zero(active_sources),
            has_demo_data=_scalar_or_zero(has_demo_data) > 0,
            latest_sync_status=latest_sync.status if latest_sync is not None else None,
            latest_sync_completed_at=latest_sync.completed_at if latest_sync is not None else None,
            latest_sync_error_code=latest_sync.error_code if latest_sync is not None else None,
        ),
    )


@router.get("/activities/recent", response_model=DashboardRecentActivitiesResponse)
def get_recent_activities(
    current_user: Annotated[AppUser, Depends(get_current_app_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> DashboardRecentActivitiesResponse:
    activities = db.scalars(
        select(Activity)
        .where(Activity.user_id == current_user.id)
        .order_by(Activity.started_at.desc())
        .limit(limit)
    ).all()

    return DashboardRecentActivitiesResponse(
        activities=[
            DashboardActivityDetail(
                id=str(activity.id),
                activity_type=activity.activity_type,
                name=activity.name,
                activity_date=activity.activity_date,
                started_at=activity.started_at,
                duration_seconds=activity.duration_seconds,
                moving_duration_seconds=activity.moving_duration_seconds,
                distance_meters=activity.distance_meters,
                calories=activity.calories,
                average_heart_rate=activity.average_heart_rate,
                training_load=activity.training_load,
            )
            for activity in activities
        ]
    )


@router.get("/sleep/trend", response_model=DashboardSleepTrendResponse)
def get_sleep_trend(
    current_user: Annotated[AppUser, Depends(get_current_app_user)],
    db: Annotated[Session, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=90)] = 14,
) -> DashboardSleepTrendResponse:
    start_date = datetime.now(UTC).date() - timedelta(days=days - 1)
    sleep_sessions = db.scalars(
        select(SleepSession)
        .where(
            SleepSession.user_id == current_user.id,
            SleepSession.sleep_date >= start_date,
        )
        .order_by(SleepSession.sleep_date.asc(), SleepSession.started_at.asc())
    ).all()

    return DashboardSleepTrendResponse(
        days=days,
        sleep_sessions=[
            DashboardSleepTrendPoint(
                id=str(sleep.id),
                sleep_date=sleep.sleep_date,
                started_at=sleep.started_at,
                ended_at=sleep.ended_at,
                total_sleep_seconds=sleep.total_sleep_seconds,
                deep_sleep_seconds=sleep.deep_sleep_seconds,
                rem_sleep_seconds=sleep.rem_sleep_seconds,
                light_sleep_seconds=sleep.light_sleep_seconds,
                awake_seconds=sleep.awake_seconds,
                sleep_score=sleep.sleep_score,
                average_spo2=sleep.average_spo2,
                average_hrv_ms=sleep.average_hrv_ms,
                average_respiration=sleep.average_respiration,
            )
            for sleep in sleep_sessions
        ],
    )


@router.get("/recovery/metrics", response_model=DashboardRecoveryMetricsResponse)
def get_recovery_metrics(
    current_user: Annotated[AppUser, Depends(get_current_app_user)],
    db: Annotated[Session, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=90)] = 14,
) -> DashboardRecoveryMetricsResponse:
    start_date = datetime.now(UTC).date() - timedelta(days=days - 1)
    metrics = db.scalars(
        select(DailyMetric)
        .where(
            DailyMetric.user_id == current_user.id,
            DailyMetric.metric_date >= start_date,
        )
        .order_by(DailyMetric.metric_date.asc())
    ).all()

    return DashboardRecoveryMetricsResponse(
        days=days,
        metrics=[
            DashboardRecoveryMetricPoint(
                metric_date=metric.metric_date,
                steps=metric.steps,
                active_seconds=metric.active_seconds,
                highly_active_seconds=metric.highly_active_seconds,
                resting_heart_rate=metric.resting_heart_rate,
                hrv_ms=metric.hrv_ms,
                stress_average=metric.stress_average,
                body_battery_min=metric.body_battery_min,
                body_battery_max=metric.body_battery_max,
                body_battery_latest=metric.body_battery_latest,
            )
            for metric in metrics
        ],
    )


@router.get("/coach/latest", response_model=DashboardInsightDetail | None)
def get_latest_coach_insight(
    current_user: Annotated[AppUser, Depends(get_current_app_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DashboardInsightDetail | None:
    latest_insight = _latest_insight_for_user(db, current_user)
    if latest_insight is None:
        return None
    return _insight_detail(latest_insight)
