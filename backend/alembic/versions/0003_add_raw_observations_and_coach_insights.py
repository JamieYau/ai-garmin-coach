"""Add raw observations and coach insights.

Revision ID: 0003_raw_coach
Revises: 0002_canonical_fitness
Create Date: 2026-07-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_raw_coach"
down_revision: str | None = "0002_canonical_fitness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "raw_observations",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_connection_id", sa.Uuid(), nullable=False),
        sa.Column("sync_run_id", sa.Uuid(), nullable=False),
        sa.Column("provider_object_type", sa.String(length=64), nullable=False),
        sa.Column("provider_object_id", sa.String(length=255), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["source_connection_id"],
            ["source_connections.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["sync_run_id"], ["sync_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_connection_id",
            "provider_object_type",
            "provider_object_id",
            name=op.f("uq_raw_observations_provider_object"),
        ),
    )
    op.create_index(
        op.f("ix_raw_observations_source_connection_id"),
        "raw_observations",
        ["source_connection_id", "provider_object_type", "provider_object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_raw_observations_sync_run_id"),
        "raw_observations",
        ["sync_run_id", "provider_object_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_raw_observations_user_id"),
        "raw_observations",
        ["user_id", "provider_object_type", "observed_at"],
        unique=False,
    )

    op.create_table(
        "coach_insights",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_sync_run_id", sa.Uuid(), nullable=True),
        sa.Column("insight_date", sa.Date(), nullable=False),
        sa.Column("insight_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("model_provider", sa.String(length=64), nullable=True),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("input_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("output", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["source_sync_run_id"],
            ["sync_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "insight_date",
            "insight_type",
            name=op.f("uq_coach_insights_user_date_type"),
        ),
    )
    op.create_index(
        op.f("ix_coach_insights_generated_at"),
        "coach_insights",
        ["generated_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_coach_insights_source_sync_run_id"),
        "coach_insights",
        ["source_sync_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_coach_insights_user_id"),
        "coach_insights",
        ["user_id", "insight_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_coach_insights_user_id"), table_name="coach_insights")
    op.drop_index(op.f("ix_coach_insights_source_sync_run_id"), table_name="coach_insights")
    op.drop_index(op.f("ix_coach_insights_generated_at"), table_name="coach_insights")
    op.drop_table("coach_insights")
    op.drop_index(op.f("ix_raw_observations_user_id"), table_name="raw_observations")
    op.drop_index(op.f("ix_raw_observations_sync_run_id"), table_name="raw_observations")
    op.drop_index(
        op.f("ix_raw_observations_source_connection_id"),
        table_name="raw_observations",
    )
    op.drop_table("raw_observations")
