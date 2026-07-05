from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class ConnectorRecordType(StrEnum):
    ACTIVITY = "activity"
    DAILY_METRIC = "daily_metric"
    SLEEP_SESSION = "sleep_session"
    BIOMETRIC_SAMPLE = "biometric_sample"


class ConnectorCredential(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=64)
    value: SecretStr


class ConnectionSetupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: uuid.UUID
    source: str = Field(min_length=1, max_length=64)
    credentials: list[ConnectorCredential] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectionSetupResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = Field(min_length=1, max_length=64)
    provider_subject_id: str | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="active")


class CredentialValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_connection_id: uuid.UUID
    credentials: list[ConnectorCredential] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CredentialValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    is_valid: bool
    requires_reauth: bool = False
    message: str | None = Field(default=None, max_length=500)


class IncrementalSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: uuid.UUID
    source_connection_id: uuid.UUID
    sync_run_id: uuid.UUID
    since: datetime | None = None
    until: datetime | None = None

    @model_validator(mode="after")
    def validate_window(self) -> IncrementalSyncRequest:
        if self.since is not None and self.until is not None and self.since > self.until:
            raise ValueError("since must be before or equal to until")
        return self


class BackfillSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: uuid.UUID
    source_connection_id: uuid.UUID
    sync_run_id: uuid.UUID
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_window(self) -> BackfillSyncRequest:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")
        return self


class ProviderPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    object_type: str = Field(min_length=1, max_length=64)
    object_id: str = Field(min_length=1, max_length=255)
    observed_at: datetime | None = None
    payload: dict[str, Any]
    payload_hash: str | None = Field(default=None, max_length=128)


class NormalizedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record_type: ConnectorRecordType
    source_record_id: str = Field(min_length=1, max_length=255)
    data: dict[str, Any]


class NormalizationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_payload: ProviderPayload
    records: list[NormalizedRecord] = Field(default_factory=list)


class SyncResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_connection_id: uuid.UUID
    sync_run_id: uuid.UUID
    raw_payloads: list[ProviderPayload] = Field(default_factory=list)
    normalized_records: list[NormalizedRecord] = Field(default_factory=list)
    error_message: str | None = Field(default=None, max_length=500)

    @property
    def raw_payload_count(self) -> int:
        return len(self.raw_payloads)

    @property
    def normalized_record_count(self) -> int:
        return len(self.normalized_records)
