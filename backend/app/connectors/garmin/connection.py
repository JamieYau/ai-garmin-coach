from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.garmin.client import (
    GarminAuthenticationError,
    GarminClient,
    GarminClientError,
    GarminConnectionError,
    GarminCredentials,
    GarminMfaRequiredError,
    GarminRateLimitError,
)
from app.connectors.garmin.metadata import GARMIN_SOURCE_METADATA
from app.core.security import encrypt_json_payload
from app.models import AppUser, SourceConnection
from app.schemas.connections import ConnectionResponse, GarminConnectionCreate


class GarminConnectionClient(Protocol):
    def login(self) -> object: ...

    def get_user_profile(self) -> dict[str, Any]: ...

    def get_full_name(self) -> str | None: ...

    def dump_tokenstore(self) -> str: ...


GarminConnectionClientBuilder = Callable[
    [GarminCredentials, Callable[[], str] | None, bool],
    GarminConnectionClient,
]


@dataclass(frozen=True)
class GarminConnectionSettings:
    encryption_secret: str


def build_garmin_connection_client(
    credentials: GarminCredentials,
    prompt_mfa: Callable[[], str] | None,
    is_cn: bool,
) -> GarminConnectionClient:
    return GarminClient(credentials, prompt_mfa=prompt_mfa, is_cn=is_cn)


class GarminConnectionService:
    def __init__(
        self,
        settings: GarminConnectionSettings,
        *,
        client_builder: GarminConnectionClientBuilder = build_garmin_connection_client,
    ) -> None:
        self._settings = settings
        self._client_builder = client_builder

    def setup_connection(
        self,
        db: Session,
        user: AppUser,
        request: GarminConnectionCreate,
    ) -> ConnectionResponse:
        credentials = GarminCredentials(
            username=request.username,
            password=request.password.get_secret_value(),
        )
        client = self._client_builder(
            credentials,
            self._mfa_prompt(request.mfa_code.get_secret_value() if request.mfa_code else None),
            request.is_cn,
        )

        try:
            client.login()
        except GarminMfaRequiredError:
            return ConnectionResponse(
                source=GARMIN_SOURCE_METADATA.source,
                status="mfa_required",
                requires_mfa=True,
                message="Garmin requires a multi-factor authentication code.",
            )

        profile = client.get_user_profile()
        full_name = client.get_full_name()
        tokenstore = client.dump_tokenstore()
        connection = self._upsert_connection(
            db=db,
            user=user,
            request=request,
            profile=profile,
            display_name=full_name or self._display_name_from_profile(profile),
            encrypted_tokenstore=encrypt_json_payload(
                {"tokenstore": tokenstore},
                self._settings.encryption_secret,
            ),
        )
        return ConnectionResponse(
            id=connection.id,
            source=connection.source,
            status=connection.status,
            provider_subject_id=connection.provider_subject_id,
            display_name=connection.display_name,
        )

    def _upsert_connection(
        self,
        *,
        db: Session,
        user: AppUser,
        request: GarminConnectionCreate,
        profile: dict[str, Any],
        display_name: str | None,
        encrypted_tokenstore: dict[str, str | int],
    ) -> SourceConnection:
        connection = db.scalar(
            select(SourceConnection).where(
                SourceConnection.user_id == user.id,
                SourceConnection.source == GARMIN_SOURCE_METADATA.source,
            )
        )
        if connection is None:
            connection = SourceConnection(user=user, source=GARMIN_SOURCE_METADATA.source)
            db.add(connection)

        connection.status = "active"
        connection.provider_subject_id = self._provider_subject_id(profile, request.username)
        connection.display_name = display_name
        connection.connection_metadata = {
            "region": "cn" if request.is_cn else "global",
            "username_hash": self._hash_identifier(request.username),
            "session_material": encrypted_tokenstore,
            "session_material_type": "garminconnect_tokenstore",
            "mfa_completed": request.mfa_code is not None,
        }
        db.commit()
        db.refresh(connection)
        return connection

    def _mfa_prompt(self, mfa_code: str | None) -> Callable[[], str]:
        def prompt() -> str:
            if mfa_code is None:
                raise GarminMfaRequiredError("Garmin requires multi-factor authentication.")
            return mfa_code

        return prompt

    def _provider_subject_id(self, profile: dict[str, Any], username: str) -> str:
        for key in ("profileId", "userProfileId", "id", "displayName"):
            value = profile.get(key)
            if value is not None:
                return str(value)
        return self._hash_identifier(username)

    def _display_name_from_profile(self, profile: dict[str, Any]) -> str | None:
        for key in ("fullName", "displayName", "userName"):
            value = profile.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    def _hash_identifier(self, value: str) -> str:
        return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


__all__ = [
    "GarminAuthenticationError",
    "GarminClientError",
    "GarminConnectionError",
    "GarminConnectionService",
    "GarminConnectionSettings",
    "GarminMfaRequiredError",
    "GarminRateLimitError",
]
