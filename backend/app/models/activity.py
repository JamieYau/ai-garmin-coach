from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.source_connection import SourceConnection
    from app.models.user import AppUser


class Activity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "activities"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_activity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    moving_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    distance_meters: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    calories: Mapped[int | None] = mapped_column(Integer)
    active_calories: Mapped[int | None] = mapped_column(Integer)
    average_heart_rate: Mapped[int | None] = mapped_column(Integer)
    max_heart_rate: Mapped[int | None] = mapped_column(Integer)
    elevation_gain_meters: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    training_load: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped[AppUser] = relationship(back_populates="activities")
    source_connection: Mapped[SourceConnection] = relationship(back_populates="activities")

    __table_args__ = (
        UniqueConstraint("source_connection_id", "source_activity_id"),
        CheckConstraint("duration_seconds >= 0", name="activities_duration_seconds_non_negative"),
        CheckConstraint(
            "moving_duration_seconds IS NULL OR moving_duration_seconds >= 0",
            name="activities_moving_duration_seconds_non_negative",
        ),
        CheckConstraint(
            "distance_meters IS NULL OR distance_meters >= 0",
            name="activities_distance_meters_non_negative",
        ),
        CheckConstraint(
            "calories IS NULL OR calories >= 0", name="activities_calories_non_negative"
        ),
        CheckConstraint(
            "active_calories IS NULL OR active_calories >= 0",
            name="activities_active_calories_non_negative",
        ),
        CheckConstraint(
            "average_heart_rate IS NULL OR average_heart_rate >= 0",
            name="activities_average_heart_rate_non_negative",
        ),
        CheckConstraint(
            "max_heart_rate IS NULL OR max_heart_rate >= 0",
            name="activities_max_heart_rate_non_negative",
        ),
        Index(None, "user_id", "activity_date"),
        Index(None, "source_connection_id", "started_at"),
        Index(None, "activity_type", "activity_date"),
    )

    def __repr__(self) -> str:
        return (
            f"Activity(id={self.id!s}, type={self.activity_type!r}, started_at={self.started_at!r})"
        )
