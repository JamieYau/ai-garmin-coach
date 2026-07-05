from __future__ import annotations

from typing import Protocol

from app.schemas.connectors import (
    BackfillSyncRequest,
    ConnectionSetupRequest,
    ConnectionSetupResult,
    CredentialValidationRequest,
    CredentialValidationResult,
    IncrementalSyncRequest,
    NormalizationResult,
    ProviderPayload,
    SyncResult,
)


class FitnessConnector(Protocol):
    """Connector contract for source-specific fitness providers."""

    source: str

    async def setup_connection(self, request: ConnectionSetupRequest) -> ConnectionSetupResult:
        """Validate setup input and return source connection metadata."""

    async def validate_credentials(
        self,
        request: CredentialValidationRequest,
    ) -> CredentialValidationResult:
        """Check whether stored or supplied credentials can still access the source."""

    async def sync_incremental(self, request: IncrementalSyncRequest) -> SyncResult:
        """Fetch provider changes since the last successful sync window."""

    async def sync_backfill(self, request: BackfillSyncRequest) -> SyncResult:
        """Fetch provider records for an explicit historical date range."""

    def normalize_payload(self, payload: ProviderPayload) -> NormalizationResult:
        """Convert one provider payload into connector-neutral records."""
