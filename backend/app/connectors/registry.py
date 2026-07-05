from __future__ import annotations

from types import MappingProxyType

from app.connectors.demo.metadata import DEMO_SOURCE_METADATA
from app.connectors.garmin.metadata import GARMIN_SOURCE_METADATA
from app.schemas.connectors import SourceCategory, SourceMetadata

FUTURE_SOURCE_CATEGORIES: tuple[SourceCategory, ...] = (
    SourceCategory.FITNESS,
    SourceCategory.RECOVERY,
    SourceCategory.CALENDAR,
    SourceCategory.NUTRITION,
    SourceCategory.MOOD,
    SourceCategory.HABITS,
)

_SOURCE_METADATA = {
    GARMIN_SOURCE_METADATA.source: GARMIN_SOURCE_METADATA,
    DEMO_SOURCE_METADATA.source: DEMO_SOURCE_METADATA,
}

SOURCE_METADATA = MappingProxyType(_SOURCE_METADATA)


def list_sources(*, include_disabled: bool = False) -> tuple[SourceMetadata, ...]:
    sources = SOURCE_METADATA.values()
    if include_disabled:
        return tuple(sources)
    return tuple(source for source in sources if source.enabled)


def get_source_metadata(source: str) -> SourceMetadata | None:
    return SOURCE_METADATA.get(source)


def require_source_metadata(source: str) -> SourceMetadata:
    metadata = get_source_metadata(source)
    if metadata is None:
        raise KeyError(f"Unknown source: {source}")
    return metadata
