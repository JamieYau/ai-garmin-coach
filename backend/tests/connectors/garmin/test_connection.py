from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.connectors.garmin.client import GarminCredentials, GarminMfaRequiredError
from app.connectors.garmin.connection import (
    GarminConnectionClient,
    GarminConnectionService,
    GarminConnectionSettings,
)
from app.core.security import decrypt_json_payload
from app.db.models import Base
from app.models import AppUser, SourceConnection
from app.schemas.connections import GarminConnectionCreate


class FakeGarminConnectionClient:
    def __init__(self, *, requires_mfa: bool = False) -> None:
        self.requires_mfa = requires_mfa
        self.prompt_mfa: Callable[[], str] | None = None

    def login(self) -> object:
        if self.requires_mfa and self.prompt_mfa is not None:
            self.prompt_mfa()
        return object()

    def get_user_profile(self) -> dict[str, Any]:
        return {"profileId": 123, "displayName": "runner-display"}

    def get_full_name(self) -> str | None:
        return "Runner Example"

    def dump_tokenstore(self) -> str:
        return "serialized-garmin-session"


def _create_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _create_user(db: Session) -> AppUser:
    user = AppUser(
        better_auth_user_id="better-auth-user-1",
        email="runner@example.com",
        display_name="Runner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_garmin_connection_setup_persists_encrypted_session_metadata() -> None:
    db = _create_session()
    user = _create_user(db)
    seen_credentials: list[GarminCredentials] = []

    def builder(
        credentials: GarminCredentials,
        prompt_mfa: Callable[[], str] | None,
        is_cn: bool,
    ) -> GarminConnectionClient:
        assert prompt_mfa is not None
        assert is_cn is False
        seen_credentials.append(credentials)
        return FakeGarminConnectionClient()

    service = GarminConnectionService(
        GarminConnectionSettings(encryption_secret="test-secret"),
        client_builder=builder,
    )

    response = service.setup_connection(
        db,
        user,
        GarminConnectionCreate(
            username="runner@example.com",
            password=SecretStr("garmin-password"),
        ),
    )

    connection = db.scalar(select(SourceConnection).where(SourceConnection.id == response.id))
    assert connection is not None
    assert response.status == "active"
    assert response.provider_subject_id == "123"
    assert response.display_name == "Runner Example"
    assert connection.connection_metadata["username_hash"] != "runner@example.com"
    assert "garmin-password" not in str(connection.connection_metadata)
    encrypted = connection.connection_metadata["session_material"]
    assert "serialized-garmin-session" not in str(encrypted)
    assert decrypt_json_payload(encrypted, "test-secret") == {
        "tokenstore": "serialized-garmin-session"
    }
    assert repr(seen_credentials[0]).find("garmin-password") == -1

    db.close()


def test_garmin_connection_setup_updates_existing_connection() -> None:
    db = _create_session()
    user = _create_user(db)
    existing = SourceConnection(
        user=user,
        source="garmin",
        status="reauth_required",
        provider_subject_id="old-id",
        display_name="Old",
        connection_metadata={"stale": True},
    )
    db.add(existing)
    db.commit()
    existing_id = existing.id

    service = GarminConnectionService(
        GarminConnectionSettings(encryption_secret="test-secret"),
        client_builder=lambda *_: FakeGarminConnectionClient(),
    )

    response = service.setup_connection(
        db,
        user,
        GarminConnectionCreate(
            username="runner@example.com",
            password=SecretStr("garmin-password"),
            mfa_code=SecretStr("123456"),
            is_cn=True,
        ),
    )

    assert response.id == existing_id
    db.refresh(existing)
    assert existing.status == "active"
    assert existing.provider_subject_id == "123"
    assert existing.connection_metadata["region"] == "cn"
    assert existing.connection_metadata["mfa_completed"] is True

    db.close()


def test_garmin_connection_setup_reports_mfa_required_without_persisting_password() -> None:
    db = _create_session()
    user = _create_user(db)

    def builder(
        credentials: GarminCredentials,
        prompt_mfa: Callable[[], str] | None,
        is_cn: bool,
    ) -> GarminConnectionClient:
        client = FakeGarminConnectionClient(requires_mfa=True)
        client.prompt_mfa = prompt_mfa
        return client

    service = GarminConnectionService(
        GarminConnectionSettings(encryption_secret="test-secret"),
        client_builder=builder,
    )

    response = service.setup_connection(
        db,
        user,
        GarminConnectionCreate(
            username="runner@example.com",
            password=SecretStr("garmin-password"),
        ),
    )

    assert response.id is None
    assert response.status == "mfa_required"
    assert response.requires_mfa is True
    assert db.scalars(select(SourceConnection)).all() == []

    db.close()


def test_garmin_connection_setup_uses_supplied_mfa_code() -> None:
    db = _create_session()
    user = _create_user(db)
    prompted_codes: list[str] = []

    def builder(
        credentials: GarminCredentials,
        prompt_mfa: Callable[[], str] | None,
        is_cn: bool,
    ) -> GarminConnectionClient:
        assert prompt_mfa is not None
        prompted_codes.append(prompt_mfa())
        return FakeGarminConnectionClient()

    service = GarminConnectionService(
        GarminConnectionSettings(encryption_secret="test-secret"),
        client_builder=builder,
    )

    service.setup_connection(
        db,
        user,
        GarminConnectionCreate(
            username="runner@example.com",
            password=SecretStr("garmin-password"),
            mfa_code=SecretStr("123456"),
        ),
    )

    assert prompted_codes == ["123456"]

    db.close()


def test_garmin_connection_mfa_prompt_raises_when_code_is_missing() -> None:
    db = _create_session()
    user = _create_user(db)

    def builder(
        credentials: GarminCredentials,
        prompt_mfa: Callable[[], str] | None,
        is_cn: bool,
    ) -> GarminConnectionClient:
        assert prompt_mfa is not None
        with pytest.raises(GarminMfaRequiredError):
            prompt_mfa()
        return FakeGarminConnectionClient()

    service = GarminConnectionService(
        GarminConnectionSettings(encryption_secret="test-secret"),
        client_builder=builder,
    )

    response = service.setup_connection(
        db,
        user,
        GarminConnectionCreate(
            username="runner@example.com",
            password=SecretStr("garmin-password"),
        ),
    )

    assert response.status == "active"

    db.close()
