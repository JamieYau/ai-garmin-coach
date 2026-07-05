import pytest

from app.connectors.demo.metadata import DEMO_SOURCE_METADATA
from app.connectors.garmin.metadata import GARMIN_SOURCE_METADATA
from app.connectors.registry import (
    FUTURE_SOURCE_CATEGORIES,
    SOURCE_METADATA,
    get_source_metadata,
    list_sources,
    require_source_metadata,
)
from app.schemas.connectors import SourceCapability, SourceCategory


def test_registry_lists_mvp_sources() -> None:
    sources = list_sources()

    assert sources == (GARMIN_SOURCE_METADATA, DEMO_SOURCE_METADATA)
    assert tuple(SOURCE_METADATA) == ("garmin", "demo")


def test_garmin_metadata_declares_mvp_sync_capabilities() -> None:
    metadata = require_source_metadata("garmin")

    assert metadata.display_name == "Garmin"
    assert metadata.category is SourceCategory.FITNESS
    assert metadata.enabled is True
    assert SourceCapability.CONNECTION_SETUP in metadata.capabilities
    assert SourceCapability.CREDENTIAL_VALIDATION in metadata.capabilities
    assert SourceCapability.ACTIVITY_SYNC in metadata.capabilities
    assert SourceCapability.DAILY_METRIC_SYNC in metadata.capabilities
    assert SourceCapability.SLEEP_SYNC in metadata.capabilities
    assert SourceCapability.BIOMETRIC_SYNC in metadata.capabilities


def test_demo_metadata_is_registered_without_credential_setup() -> None:
    metadata = require_source_metadata("demo")

    assert metadata is DEMO_SOURCE_METADATA
    assert metadata.category is SourceCategory.DEMO
    assert SourceCapability.CONNECTION_SETUP not in metadata.capabilities
    assert SourceCapability.BACKFILL_SYNC in metadata.capabilities


def test_unknown_sources_are_not_registered() -> None:
    assert get_source_metadata("strava") is None

    with pytest.raises(KeyError, match="Unknown source: strava"):
        require_source_metadata("strava")


def test_future_extension_categories_exist_without_registering_sources() -> None:
    assert SourceCategory.CALENDAR in FUTURE_SOURCE_CATEGORIES
    assert SourceCategory.NUTRITION in FUTURE_SOURCE_CATEGORIES
    assert SourceCategory.MOOD in FUTURE_SOURCE_CATEGORIES
    assert SourceCategory.HABITS in FUTURE_SOURCE_CATEGORIES
    assert get_source_metadata("oura") is None
    assert get_source_metadata("apple_health") is None
    assert get_source_metadata("google_fit") is None
