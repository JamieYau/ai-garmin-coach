from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
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


class BiometricSample(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "biometric_samples"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_sample_id: Mapped[str | None] = mapped_column(String(255))
    sample_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    aggregation_window_seconds: Mapped[int | None] = mapped_column(Integer)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped[AppUser] = relationship(back_populates="biometric_samples")
    source_connection: Mapped[SourceConnection] = relationship(back_populates="biometric_samples")

    __table_args__ = (
        UniqueConstraint(
            "source_connection_id",
            "sample_type",
            "sampled_at",
            name="uq_biometric_samples_source_connection_sample_time",
        ),
        UniqueConstraint(
            "source_connection_id",
            "source_sample_id",
            name="uq_biometric_samples_source_connection_sample_id",
        ),
        CheckConstraint(
            "sample_type IN ('heart_rate', 'hrv', 'stress', 'body_battery', 'spo2', 'respiration')",
            name="biometric_samples_sample_type_valid",
        ),
        CheckConstraint(
            "aggregation_window_seconds IS NULL OR aggregation_window_seconds >= 0",
            name="biometric_samples_aggregation_window_seconds_non_negative",
        ),
        Index(None, "user_id", "sample_type", "sampled_at"),
        Index(None, "source_connection_id", "sampled_at"),
    )

    def __repr__(self) -> str:
        return f"BiometricSample(id={self.id!s}, sample_type={self.sample_type!r})"
