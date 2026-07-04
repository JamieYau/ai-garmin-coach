from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.source_connection import SourceConnection
    from app.models.user import AppUser


class SyncRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sync_runs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    sync_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)

    user: Mapped[AppUser] = relationship(back_populates="sync_runs")
    source_connection: Mapped[SourceConnection] = relationship(back_populates="sync_runs")

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="sync_runs_status_valid",
        ),
        CheckConstraint(
            "sync_type IN ('manual', 'scheduled', 'backfill')",
            name="sync_runs_sync_type_valid",
        ),
        CheckConstraint("records_seen >= 0", name="sync_runs_records_seen_non_negative"),
        CheckConstraint("records_imported >= 0", name="sync_runs_records_imported_non_negative"),
        Index(None, "user_id", "status"),
        Index(None, "source_connection_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"SyncRun(id={self.id!s}, status={self.status!r}, sync_type={self.sync_type!r})"
