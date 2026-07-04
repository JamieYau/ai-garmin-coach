from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.source_connection import SourceConnection
    from app.models.user import AppUser


class DailyMetric(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "daily_metrics"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    steps: Mapped[int | None] = mapped_column(Integer)
    calories: Mapped[int | None] = mapped_column(Integer)
    active_calories: Mapped[int | None] = mapped_column(Integer)
    floors_ascended: Mapped[int | None] = mapped_column(Integer)
    active_seconds: Mapped[int | None] = mapped_column(Integer)
    highly_active_seconds: Mapped[int | None] = mapped_column(Integer)
    resting_heart_rate: Mapped[int | None] = mapped_column(Integer)
    hrv_ms: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    stress_average: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    body_battery_min: Mapped[int | None] = mapped_column(Integer)
    body_battery_max: Mapped[int | None] = mapped_column(Integer)
    body_battery_latest: Mapped[int | None] = mapped_column(Integer)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped[AppUser] = relationship(back_populates="daily_metrics")
    source_connection: Mapped[SourceConnection] = relationship(back_populates="daily_metrics")

    __table_args__ = (
        UniqueConstraint("source_connection_id", "metric_date"),
        CheckConstraint("steps IS NULL OR steps >= 0", name="daily_metrics_steps_non_negative"),
        CheckConstraint(
            "calories IS NULL OR calories >= 0",
            name="daily_metrics_calories_non_negative",
        ),
        CheckConstraint(
            "active_calories IS NULL OR active_calories >= 0",
            name="daily_metrics_active_calories_non_negative",
        ),
        CheckConstraint(
            "floors_ascended IS NULL OR floors_ascended >= 0",
            name="daily_metrics_floors_ascended_non_negative",
        ),
        CheckConstraint(
            "active_seconds IS NULL OR active_seconds >= 0",
            name="daily_metrics_active_seconds_non_negative",
        ),
        CheckConstraint(
            "highly_active_seconds IS NULL OR highly_active_seconds >= 0",
            name="daily_metrics_highly_active_seconds_non_negative",
        ),
        Index(None, "user_id", "metric_date"),
    )

    def __repr__(self) -> str:
        return f"DailyMetric(id={self.id!s}, metric_date={self.metric_date!r})"
