"""Add user and sync metadata tables.

Revision ID: 0001_user_sync_metadata
Revises:
Create Date: 2026-07-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_user_sync_metadata"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_users",
        sa.Column("better_auth_user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("better_auth_user_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(
        op.f("ix_app_users_better_auth_user_id"),
        "app_users",
        ["better_auth_user_id"],
        unique=False,
    )

    op.create_table(
        "source_connections",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_subject_id", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'reauth_required', 'disconnected')",
            name=op.f("ck_source_connections_source_connections_status_valid"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source"),
    )
    op.create_index(
        op.f("ix_source_connections_source"),
        "source_connections",
        ["source", "provider_subject_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_connections_user_id"),
        "source_connections",
        ["user_id", "status"],
        unique=False,
    )

    op.create_table(
        "sync_runs",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_connection_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sync_type", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_seen", sa.Integer(), nullable=False),
        sa.Column("records_imported", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "records_imported >= 0",
            name=op.f("ck_sync_runs_sync_runs_records_imported_non_negative"),
        ),
        sa.CheckConstraint(
            "records_seen >= 0",
            name=op.f("ck_sync_runs_sync_runs_records_seen_non_negative"),
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name=op.f("ck_sync_runs_sync_runs_status_valid"),
        ),
        sa.CheckConstraint(
            "sync_type IN ('manual', 'scheduled', 'backfill')",
            name=op.f("ck_sync_runs_sync_runs_sync_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["source_connection_id"],
            ["source_connections.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sync_runs_source_connection_id"),
        "sync_runs",
        ["source_connection_id", "created_at"],
        unique=False,
    )
    op.create_index(op.f("ix_sync_runs_user_id"), "sync_runs", ["user_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sync_runs_user_id"), table_name="sync_runs")
    op.drop_index(op.f("ix_sync_runs_source_connection_id"), table_name="sync_runs")
    op.drop_table("sync_runs")
    op.drop_index(op.f("ix_source_connections_user_id"), table_name="source_connections")
    op.drop_index(op.f("ix_source_connections_source"), table_name="source_connections")
    op.drop_table("source_connections")
    op.drop_index(op.f("ix_app_users_better_auth_user_id"), table_name="app_users")
    op.drop_table("app_users")
