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


class SleepSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sleep_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_sleep_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sleep_date: Mapped[date] = mapped_column(Date, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_sleep_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    deep_sleep_seconds: Mapped[int | None] = mapped_column(Integer)
    rem_sleep_seconds: Mapped[int | None] = mapped_column(Integer)
    light_sleep_seconds: Mapped[int | None] = mapped_column(Integer)
    awake_seconds: Mapped[int | None] = mapped_column(Integer)
    sleep_score: Mapped[int | None] = mapped_column(Integer)
    average_spo2: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    average_hrv_ms: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    average_respiration: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped[AppUser] = relationship(back_populates="sleep_sessions")
    source_connection: Mapped[SourceConnection] = relationship(back_populates="sleep_sessions")

    __table_args__ = (
        UniqueConstraint("source_connection_id", "source_sleep_id"),
        CheckConstraint(
            "total_sleep_seconds >= 0",
            name="sleep_sessions_total_sleep_seconds_non_negative",
        ),
        CheckConstraint(
            "deep_sleep_seconds IS NULL OR deep_sleep_seconds >= 0",
            name="sleep_sessions_deep_sleep_seconds_non_negative",
        ),
        CheckConstraint(
            "rem_sleep_seconds IS NULL OR rem_sleep_seconds >= 0",
            name="sleep_sessions_rem_sleep_seconds_non_negative",
        ),
        CheckConstraint(
            "light_sleep_seconds IS NULL OR light_sleep_seconds >= 0",
            name="sleep_sessions_light_sleep_seconds_non_negative",
        ),
        CheckConstraint(
            "awake_seconds IS NULL OR awake_seconds >= 0",
            name="sleep_sessions_awake_seconds_non_negative",
        ),
        CheckConstraint(
            "sleep_score IS NULL OR (sleep_score >= 0 AND sleep_score <= 100)",
            name="sleep_sessions_sleep_score_range",
        ),
        Index(None, "user_id", "sleep_date"),
        Index(None, "source_connection_id", "started_at"),
    )

    def __repr__(self) -> str:
        return f"SleepSession(id={self.id!s}, sleep_date={self.sleep_date!r})"
