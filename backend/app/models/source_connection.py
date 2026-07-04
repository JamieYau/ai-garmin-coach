from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.sync_run import SyncRun
    from app.models.user import AppUser


class SourceConnection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "source_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    provider_subject_id: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    connection_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[AppUser] = relationship(back_populates="source_connections")
    sync_runs: Mapped[list[SyncRun]] = relationship(
        back_populates="source_connection",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'paused', 'reauth_required', 'disconnected')",
            name="source_connections_status_valid",
        ),
        UniqueConstraint("user_id", "source"),
        Index(None, "user_id", "status"),
        Index(None, "source", "provider_subject_id"),
    )

    def __repr__(self) -> str:
        return f"SourceConnection(id={self.id!s}, source={self.source!r}, status={self.status!r})"
