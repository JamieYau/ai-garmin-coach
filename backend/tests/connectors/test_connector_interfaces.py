from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.connectors.base import FitnessConnector
from app.schemas.connectors import (
    BackfillSyncRequest,
    ConnectionSetupRequest,
    ConnectionSetupResult,
    ConnectorCredential,
    ConnectorRecordType,
    CredentialValidationRequest,
    CredentialValidationResult,
    IncrementalSyncRequest,
    NormalizationResult,
    NormalizedRecord,
    ProviderPayload,
    SyncResult,
)


class StubConnector:
    source = "stub"

    async def setup_connection(self, request: ConnectionSetupRequest) -> ConnectionSetupResult:
        return ConnectionSetupResult(
            source=request.source,
            provider_subject_id="stub-user",
            display_name="Stub User",
            metadata={"mode": "test"},
        )

    async def validate_credentials(
        self,
        request: CredentialValidationRequest,
    ) -> CredentialValidationResult:
        return CredentialValidationResult(is_valid=bool(request.credentials))

    async def sync_incremental(self, request: IncrementalSyncRequest) -> SyncResult:
        payload = ProviderPayload(
            object_type="activity",
            object_id="activity-1",
            observed_at=request.until,
            payload={"activityId": 1},
        )
        normalized = self.normalize_payload(payload).records
        return SyncResult(
            source_connection_id=request.source_connection_id,
            sync_run_id=request.sync_run_id,
            raw_payloads=[payload],
            normalized_records=normalized,
        )

    async def sync_backfill(self, request: BackfillSyncRequest) -> SyncResult:
        return SyncResult(
            source_connection_id=request.source_connection_id,
            sync_run_id=request.sync_run_id,
        )

    def normalize_payload(self, payload: ProviderPayload) -> NormalizationResult:
        return NormalizationResult(
            raw_payload=payload,
            records=[
                NormalizedRecord(
                    record_type=ConnectorRecordType.ACTIVITY,
                    source_record_id=payload.object_id,
                    data={"source_activity_id": payload.object_id},
                )
            ],
        )


def test_connector_protocol_accepts_expected_methods() -> None:
    connector: FitnessConnector = StubConnector()

    assert connector.source == "stub"


@pytest.mark.anyio
async def test_connector_contract_round_trip() -> None:
    connector: FitnessConnector = StubConnector()
    user_id = uuid4()
    source_connection_id = uuid4()
    sync_run_id = uuid4()

    setup_result = await connector.setup_connection(
        ConnectionSetupRequest(
            user_id=user_id,
            source="stub",
            credentials=[ConnectorCredential(name="api_key", value="secret")],
        )
    )
    validation_result = await connector.validate_credentials(
        CredentialValidationRequest(
            source_connection_id=source_connection_id,
            credentials=[ConnectorCredential(name="api_key", value="secret")],
        )
    )
    sync_result = await connector.sync_incremental(
        IncrementalSyncRequest(
            user_id=user_id,
            source_connection_id=source_connection_id,
            sync_run_id=sync_run_id,
            since=datetime(2026, 7, 1, tzinfo=UTC),
            until=datetime(2026, 7, 5, tzinfo=UTC),
        )
    )

    assert setup_result.provider_subject_id == "stub-user"
    assert validation_result.is_valid is True
    assert sync_result.raw_payload_count == 1
    assert sync_result.normalized_record_count == 1
    assert sync_result.normalized_records[0].record_type is ConnectorRecordType.ACTIVITY


def test_credentials_are_secret_in_string_representations() -> None:
    request = ConnectionSetupRequest(
        user_id=uuid4(),
        source="garmin",
        credentials=[ConnectorCredential(name="password", value="super-secret")],
    )

    rendered = repr(request)
    dumped: dict[str, Any] = request.model_dump()

    assert "super-secret" not in rendered
    assert str(dumped["credentials"][0]["value"]) == "**********"


def test_sync_windows_reject_inverted_ranges() -> None:
    with pytest.raises(ValidationError):
        IncrementalSyncRequest(
            user_id=uuid4(),
            source_connection_id=uuid4(),
            sync_run_id=uuid4(),
            since=datetime(2026, 7, 5, tzinfo=UTC),
            until=datetime(2026, 7, 1, tzinfo=UTC),
        )

    with pytest.raises(ValidationError):
        BackfillSyncRequest(
            user_id=uuid4(),
            source_connection_id=uuid4(),
            sync_run_id=uuid4(),
            start_date=date(2026, 7, 5),
            end_date=date(2026, 7, 1),
        )


def test_provider_payload_and_normalized_record_require_provider_identity() -> None:
    with pytest.raises(ValidationError):
        ProviderPayload(object_type="", object_id="activity-1", payload={})

    with pytest.raises(ValidationError):
        NormalizedRecord(
            record_type=ConnectorRecordType.ACTIVITY,
            source_record_id="",
            data={},
        )
