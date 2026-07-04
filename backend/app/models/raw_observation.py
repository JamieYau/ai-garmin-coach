from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.source_connection import SourceConnection
    from app.models.sync_run import SyncRun
    from app.models.user import AppUser


class RawObservation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "raw_observations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    sync_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sync_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_object_id: Mapped[str] = mapped_column(String(255), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    payload_hash: Mapped[str | None] = mapped_column(String(128))

    user: Mapped[AppUser] = relationship(back_populates="raw_observations")
    source_connection: Mapped[SourceConnection] = relationship(back_populates="raw_observations")
    sync_run: Mapped[SyncRun] = relationship(back_populates="raw_observations")

    __table_args__ = (
        UniqueConstraint(
            "source_connection_id",
            "provider_object_type",
            "provider_object_id",
            name="uq_raw_observations_provider_object",
        ),
        Index(None, "user_id", "provider_object_type", "observed_at"),
        Index(None, "sync_run_id", "provider_object_type"),
        Index(None, "source_connection_id", "provider_object_type", "provider_object_id"),
    )

    def __repr__(self) -> str:
        return (
            "RawObservation("
            f"id={self.id!s}, type={self.provider_object_type!r}, "
            f"provider_object_id={self.provider_object_id!r})"
        )
