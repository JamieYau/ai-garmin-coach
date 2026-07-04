from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.sync_run import SyncRun
    from app.models.user import AppUser


class CoachInsight(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "coach_insights"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_sync_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sync_runs.id", ondelete="SET NULL"),
    )
    insight_date: Mapped[date] = mapped_column(Date, nullable=False)
    insight_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str | None] = mapped_column(Text)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    model_provider: Mapped[str | None] = mapped_column(String(64))
    model_name: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    input_fingerprint: Mapped[str | None] = mapped_column(String(128))
    output: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[AppUser] = relationship(back_populates="coach_insights")
    source_sync_run: Mapped[SyncRun | None] = relationship(back_populates="coach_insights")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "insight_date",
            "insight_type",
            name="uq_coach_insights_user_date_type",
        ),
        Index(None, "user_id", "insight_date"),
        Index(None, "source_sync_run_id"),
        Index(None, "generated_at"),
    )

    def __repr__(self) -> str:
        return (
            f"CoachInsight(id={self.id!s}, type={self.insight_type!r}, "
            f"insight_date={self.insight_date!r})"
        )
