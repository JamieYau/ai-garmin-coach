"""Add canonical fitness data tables.

Revision ID: 0002_canonical_fitness
Revises: 0001_user_sync_metadata
Create Date: 2026-07-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_canonical_fitness"
down_revision: str | None = "0001_user_sync_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "activities",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_connection_id", sa.Uuid(), nullable=False),
        sa.Column("source_activity_id", sa.String(length=255), nullable=False),
        sa.Column("activity_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("moving_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("distance_meters", sa.Numeric(10, 2), nullable=True),
        sa.Column("calories", sa.Integer(), nullable=True),
        sa.Column("active_calories", sa.Integer(), nullable=True),
        sa.Column("average_heart_rate", sa.Integer(), nullable=True),
        sa.Column("max_heart_rate", sa.Integer(), nullable=True),
        sa.Column("elevation_gain_meters", sa.Numeric(10, 2), nullable=True),
        sa.Column("training_load", sa.Numeric(8, 2), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=False),
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
            "active_calories IS NULL OR active_calories >= 0",
            name=op.f("ck_activities_activities_active_calories_non_negative"),
        ),
        sa.CheckConstraint(
            "average_heart_rate IS NULL OR average_heart_rate >= 0",
            name=op.f("ck_activities_activities_average_heart_rate_non_negative"),
        ),
        sa.CheckConstraint(
            "calories IS NULL OR calories >= 0",
            name=op.f("ck_activities_activities_calories_non_negative"),
        ),
        sa.CheckConstraint(
            "distance_meters IS NULL OR distance_meters >= 0",
            name=op.f("ck_activities_activities_distance_meters_non_negative"),
        ),
        sa.CheckConstraint(
            "duration_seconds >= 0",
            name=op.f("ck_activities_activities_duration_seconds_non_negative"),
        ),
        sa.CheckConstraint(
            "max_heart_rate IS NULL OR max_heart_rate >= 0",
            name=op.f("ck_activities_activities_max_heart_rate_non_negative"),
        ),
        sa.CheckConstraint(
            "moving_duration_seconds IS NULL OR moving_duration_seconds >= 0",
            name=op.f("ck_activities_activities_moving_duration_seconds_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["source_connection_id"], ["source_connections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_connection_id", "source_activity_id"),
    )
    op.create_index(
        op.f("ix_activities_activity_type"),
        "activities",
        ["activity_type", "activity_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_activities_source_connection_id"),
        "activities",
        ["source_connection_id", "started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_activities_user_id"), "activities", ["user_id", "activity_date"], unique=False
    )

    op.create_table(
        "daily_metrics",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_connection_id", sa.Uuid(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("calories", sa.Integer(), nullable=True),
        sa.Column("active_calories", sa.Integer(), nullable=True),
        sa.Column("floors_ascended", sa.Integer(), nullable=True),
        sa.Column("active_seconds", sa.Integer(), nullable=True),
        sa.Column("highly_active_seconds", sa.Integer(), nullable=True),
        sa.Column("resting_heart_rate", sa.Integer(), nullable=True),
        sa.Column("hrv_ms", sa.Numeric(8, 2), nullable=True),
        sa.Column("stress_average", sa.Numeric(6, 2), nullable=True),
        sa.Column("body_battery_min", sa.Integer(), nullable=True),
        sa.Column("body_battery_max", sa.Integer(), nullable=True),
        sa.Column("body_battery_latest", sa.Integer(), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=False),
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
            "active_calories IS NULL OR active_calories >= 0",
            name=op.f("ck_daily_metrics_daily_metrics_active_calories_non_negative"),
        ),
        sa.CheckConstraint(
            "active_seconds IS NULL OR active_seconds >= 0",
            name=op.f("ck_daily_metrics_daily_metrics_active_seconds_non_negative"),
        ),
        sa.CheckConstraint(
            "calories IS NULL OR calories >= 0",
            name=op.f("ck_daily_metrics_daily_metrics_calories_non_negative"),
        ),
        sa.CheckConstraint(
            "floors_ascended IS NULL OR floors_ascended >= 0",
            name=op.f("ck_daily_metrics_daily_metrics_floors_ascended_non_negative"),
        ),
        sa.CheckConstraint(
            "highly_active_seconds IS NULL OR highly_active_seconds >= 0",
            name=op.f("ck_daily_metrics_daily_metrics_highly_active_seconds_non_negative"),
        ),
        sa.CheckConstraint(
            "steps IS NULL OR steps >= 0",
            name=op.f("ck_daily_metrics_daily_metrics_steps_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["source_connection_id"], ["source_connections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_connection_id", "metric_date"),
    )
    op.create_index(
        op.f("ix_daily_metrics_user_id"),
        "daily_metrics",
        ["user_id", "metric_date"],
        unique=False,
    )

    op.create_table(
        "sleep_sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_connection_id", sa.Uuid(), nullable=False),
        sa.Column("source_sleep_id", sa.String(length=255), nullable=False),
        sa.Column("sleep_date", sa.Date(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_sleep_seconds", sa.Integer(), nullable=False),
        sa.Column("deep_sleep_seconds", sa.Integer(), nullable=True),
        sa.Column("rem_sleep_seconds", sa.Integer(), nullable=True),
        sa.Column("light_sleep_seconds", sa.Integer(), nullable=True),
        sa.Column("awake_seconds", sa.Integer(), nullable=True),
        sa.Column("sleep_score", sa.Integer(), nullable=True),
        sa.Column("average_spo2", sa.Numeric(5, 2), nullable=True),
        sa.Column("average_hrv_ms", sa.Numeric(8, 2), nullable=True),
        sa.Column("average_respiration", sa.Numeric(6, 2), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=False),
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
            "awake_seconds IS NULL OR awake_seconds >= 0",
            name=op.f("ck_sleep_sessions_sleep_sessions_awake_seconds_non_negative"),
        ),
        sa.CheckConstraint(
            "deep_sleep_seconds IS NULL OR deep_sleep_seconds >= 0",
            name=op.f("ck_sleep_sessions_sleep_sessions_deep_sleep_seconds_non_negative"),
        ),
        sa.CheckConstraint(
            "light_sleep_seconds IS NULL OR light_sleep_seconds >= 0",
            name=op.f("ck_sleep_sessions_sleep_sessions_light_sleep_seconds_non_negative"),
        ),
        sa.CheckConstraint(
            "rem_sleep_seconds IS NULL OR rem_sleep_seconds >= 0",
            name=op.f("ck_sleep_sessions_sleep_sessions_rem_sleep_seconds_non_negative"),
        ),
        sa.CheckConstraint(
            "sleep_score IS NULL OR (sleep_score >= 0 AND sleep_score <= 100)",
            name=op.f("ck_sleep_sessions_sleep_sessions_sleep_score_range"),
        ),
        sa.CheckConstraint(
            "total_sleep_seconds >= 0",
            name=op.f("ck_sleep_sessions_sleep_sessions_total_sleep_seconds_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["source_connection_id"], ["source_connections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_connection_id", "source_sleep_id"),
    )
    op.create_index(
        op.f("ix_sleep_sessions_source_connection_id"),
        "sleep_sessions",
        ["source_connection_id", "started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sleep_sessions_user_id"),
        "sleep_sessions",
        ["user_id", "sleep_date"],
        unique=False,
    )

    op.create_table(
        "biometric_samples",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_connection_id", sa.Uuid(), nullable=False),
        sa.Column("source_sample_id", sa.String(length=255), nullable=True),
        sa.Column("sample_type", sa.String(length=64), nullable=False),
        sa.Column("sampled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("aggregation_window_seconds", sa.Integer(), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=False),
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
            "aggregation_window_seconds IS NULL OR aggregation_window_seconds >= 0",
            name=op.f(
                "ck_biometric_samples_biometric_samples_aggregation_window_seconds_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "sample_type IN ('heart_rate', 'hrv', 'stress', 'body_battery', 'spo2', 'respiration')",
            name=op.f("ck_biometric_samples_biometric_samples_sample_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["source_connection_id"], ["source_connections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_connection_id",
            "sample_type",
            "sampled_at",
            name=op.f("uq_biometric_samples_source_connection_sample_time"),
        ),
        sa.UniqueConstraint(
            "source_connection_id",
            "source_sample_id",
            name=op.f("uq_biometric_samples_source_connection_sample_id"),
        ),
    )
    op.create_index(
        op.f("ix_biometric_samples_source_connection_id"),
        "biometric_samples",
        ["source_connection_id", "sampled_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_biometric_samples_user_id"),
        "biometric_samples",
        ["user_id", "sample_type", "sampled_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_biometric_samples_user_id"), table_name="biometric_samples")
    op.drop_index(op.f("ix_biometric_samples_source_connection_id"), table_name="biometric_samples")
    op.drop_table("biometric_samples")
    op.drop_index(op.f("ix_sleep_sessions_user_id"), table_name="sleep_sessions")
    op.drop_index(op.f("ix_sleep_sessions_source_connection_id"), table_name="sleep_sessions")
    op.drop_table("sleep_sessions")
    op.drop_index(op.f("ix_daily_metrics_user_id"), table_name="daily_metrics")
    op.drop_table("daily_metrics")
    op.drop_index(op.f("ix_activities_user_id"), table_name="activities")
    op.drop_index(op.f("ix_activities_source_connection_id"), table_name="activities")
    op.drop_index(op.f("ix_activities_activity_type"), table_name="activities")
    op.drop_table("activities")
