from __future__ import annotations

from app.schemas.connectors import SourceCapability, SourceCategory, SourceMetadata

DEMO_SOURCE_METADATA = SourceMetadata(
    source="demo",
    display_name="Demo Data",
    category=SourceCategory.DEMO,
    capabilities=(
        SourceCapability.INCREMENTAL_SYNC,
        SourceCapability.BACKFILL_SYNC,
        SourceCapability.ACTIVITY_SYNC,
        SourceCapability.DAILY_METRIC_SYNC,
        SourceCapability.SLEEP_SYNC,
        SourceCapability.BIOMETRIC_SYNC,
    ),
    description="Deterministic local data for development and portfolio mode.",
)
