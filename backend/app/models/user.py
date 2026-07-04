from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
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

    __table_args__ = (
        UniqueConstraint("better_auth_user_id"),
        UniqueConstraint("email"),
        Index(None, "better_auth_user_id"),
    )

    def __repr__(self) -> str:
        return f"AppUser(id={self.id!s}, better_auth_user_id={self.better_auth_user_id!r})"
