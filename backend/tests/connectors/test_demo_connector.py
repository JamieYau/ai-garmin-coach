from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.connectors.base import FitnessConnector
from app.connectors.demo import DemoConnector
from app.schemas.connectors import (
    BackfillSyncRequest,
    ConnectionSetupRequest,
    ConnectorCredential,
    ConnectorRecordType,
    CredentialValidationRequest,
    IncrementalSyncRequest,
    ProviderPayload,
    SyncResult,
    SyncStatus,
)


def test_demo_connector_implements_fitness_connector_protocol() -> None:
    connector: FitnessConnector = DemoConnector()

    assert connector.source == "demo"


@pytest.mark.anyio
async def test_demo_connector_setup_and_validation_do_not_require_credentials() -> None:
    connector = DemoConnector(seed="test-seed")
    user_id = uuid4()
    source_connection_id = uuid4()

    setup = await connector.setup_connection(
        ConnectionSetupRequest(
            user_id=user_id,
            source="demo",
            credentials=[ConnectorCredential(name="password", value="do-not-store")],
        )
    )
    validation = await connector.validate_credentials(
        CredentialValidationRequest(source_connection_id=source_connection_id)
    )

    assert setup.source == "demo"
    assert setup.provider_subject_id == f"demo-{user_id}"
    assert setup.metadata == {"seed": "test-seed", "credentials_required": False}
    assert validation.is_valid is True


@pytest.mark.anyio
async def test_demo_backfill_returns_deterministic_realistic_records() -> None:
    connector = DemoConnector(seed="stable")
    request = BackfillSyncRequest(
        user_id=uuid4(),
        source_connection_id=uuid4(),
        sync_run_id=uuid4(),
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 3),
    )

    first = await connector.sync_backfill(request)
    second = await connector.sync_backfill(request)

    assert first == second
    assert first.status is SyncStatus.SUCCEEDED
    assert first.raw_payload_count >= 9
    assert first.normalized_record_count == first.raw_payload_count
    assert {record.record_type for record in first.normalized_records} >= {
        ConnectorRecordType.DAILY_METRIC,
        ConnectorRecordType.SLEEP_SESSION,
        ConnectorRecordType.BIOMETRIC_SAMPLE,
    }
    activity = next(
        record
        for record in first.normalized_records
        if record.record_type is ConnectorRecordType.ACTIVITY
    )
    assert activity.data["activity_type"] == "running"
    assert activity.data["distance_meters"] >= 5_000
    assert activity.data["raw_data"]["activityId"] == activity.source_record_id


@pytest.mark.anyio
async def test_demo_incremental_uses_request_window() -> None:
    connector = DemoConnector(seed="stable")

    result = await connector.sync_incremental(
        IncrementalSyncRequest(
            user_id=uuid4(),
            source_connection_id=uuid4(),
            sync_run_id=uuid4(),
            since=datetime(2026, 7, 4, tzinfo=UTC),
            until=datetime(2026, 7, 4, 23, 59, tzinfo=UTC),
        )
    )

    assert result.raw_payload_count >= 3
    assert all(payload.object_id.endswith("2026-07-04") for payload in result.raw_payloads)


def test_demo_normalization_rejects_unknown_payload_types() -> None:
    connector = DemoConnector()

    with pytest.raises(ValueError, match="Unsupported demo payload type"):
        connector.normalize_payload(
            ProviderPayload(
                object_type="unknown",
                object_id="unknown-1",
                payload={"value": 1},
            )
        )


@pytest.mark.anyio
async def test_demo_sync_results_do_not_expose_credentials() -> None:
    connector = DemoConnector(seed="stable")
    secret = "very-secret-password"

    await connector.setup_connection(
        ConnectionSetupRequest(
            user_id=uuid4(),
            source="demo",
            credentials=[ConnectorCredential(name="password", value=secret)],
        )
    )
    result = await connector.sync_backfill(
        BackfillSyncRequest(
            user_id=uuid4(),
            source_connection_id=uuid4(),
            sync_run_id=uuid4(),
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 1),
        )
    )

    assert secret not in result.model_dump_json()
    assert "password" not in result.model_dump_json()


@pytest.mark.anyio
async def test_demo_connector_failures_return_failed_sync_result() -> None:
    connector = DemoConnector(seed="force-failure")

    result = await connector.sync_backfill(
        BackfillSyncRequest(
            user_id=uuid4(),
            source_connection_id=uuid4(),
            sync_run_id=uuid4(),
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 1),
        )
    )

    assert result.status is SyncStatus.FAILED
    assert result.error_code == "demo_sync_failed"
    assert result.error_message is not None
    assert result.raw_payload_count == 0
    assert result.normalized_record_count == 0


def test_failed_sync_results_require_error_message() -> None:
    with pytest.raises(ValidationError, match="failed sync results require an error_message"):
        SyncResult(
            source_connection_id=uuid4(),
            sync_run_id=uuid4(),
            status=SyncStatus.FAILED,
        )
