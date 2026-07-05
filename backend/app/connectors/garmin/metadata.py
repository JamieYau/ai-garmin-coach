from __future__ import annotations

from app.schemas.connectors import SourceCapability, SourceCategory, SourceMetadata

GARMIN_SOURCE_METADATA = SourceMetadata(
    source="garmin",
    display_name="Garmin",
    category=SourceCategory.FITNESS,
    capabilities=(
        SourceCapability.CONNECTION_SETUP,
        SourceCapability.CREDENTIAL_VALIDATION,
        SourceCapability.INCREMENTAL_SYNC,
        SourceCapability.BACKFILL_SYNC,
        SourceCapability.ACTIVITY_SYNC,
        SourceCapability.DAILY_METRIC_SYNC,
        SourceCapability.SLEEP_SYNC,
        SourceCapability.BIOMETRIC_SYNC,
    ),
    description="Garmin Connect training, recovery, sleep, and biometric data.",
)
