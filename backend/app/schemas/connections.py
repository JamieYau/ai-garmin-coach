from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class GarminConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    username: str = Field(min_length=1, max_length=255)
    password: SecretStr
    mfa_code: SecretStr | None = Field(default=None, min_length=1, max_length=32)
    is_cn: bool = False


class ConnectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: uuid.UUID | None = None
    source: str = Field(min_length=1, max_length=64)
    status: str = Field(min_length=1, max_length=32)
    provider_subject_id: str | None = None
    display_name: str | None = None
    requires_mfa: bool = False
    message: str | None = None
