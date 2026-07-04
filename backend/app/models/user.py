from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.activity import Activity
    from app.models.biometric_sample import BiometricSample
    from app.models.daily_metric import DailyMetric
    from app.models.sleep_session import SleepSession
    from app.models.source_connection import SourceConnection
    from app.models.sync_run import SyncRun


class AppUser(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "app_users"

    better_auth_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")

    source_connections: Mapped[list[SourceConnection]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sync_runs: Mapped[list[SyncRun]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    activities: Mapped[list[Activity]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    daily_metrics: Mapped[list[DailyMetric]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sleep_sessions: Mapped[list[SleepSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    biometric_samples: Mapped[list[BiometricSample]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("better_auth_user_id"),
        UniqueConstraint("email"),
        Index(None, "better_auth_user_id"),
    )

    def __repr__(self) -> str:
        return f"AppUser(id={self.id!s}, better_auth_user_id={self.better_auth_user_id!r})"
