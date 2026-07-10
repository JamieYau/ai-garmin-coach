from __future__ import annotations

import json
import logging
from collections.abc import Callable, Generator
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.connections import get_garmin_connection_service
from app.api.dependencies import get_current_app_user
from app.connectors.garmin.client import GarminCredentials
from app.connectors.garmin.connection import GarminConnectionService, GarminConnectionSettings
from app.core.logging import JsonLogFormatter, SensitiveDataFilter, redact_sensitive_data
from app.core.security import decrypt_sensitive_payload, encrypt_sensitive_payload
from app.db.models import Base
from app.db.session import get_db
from app.main import create_app
from app.models import AppUser, SourceConnection


class FakeGarminClient:
    def __init__(self, credentials: GarminCredentials) -> None:
        self.credentials = credentials

    def login(self) -> object:
        return object()

    def get_user_profile(self) -> dict[str, Any]:
        return {"profileId": "garmin-profile-1", "displayName": "runner"}

    def get_full_name(self) -> str | None:
        return "Runner Example"

    def dump_tokenstore(self) -> str:
        return "plain-garmin-tokenstore"


def test_sensitive_payload_encryption_round_trips_without_plaintext() -> None:
    envelope = encrypt_sensitive_payload(
        {"tokenstore": "plain-garmin-tokenstore"},
        "test-secret-with-enough-length-for-local-tests",
    )

    rendered = json.dumps(envelope)

    assert envelope["algorithm"] == "fernet-sha256"
    assert "plain-garmin-tokenstore" not in rendered
    assert decrypt_sensitive_payload(
        envelope,
        "test-secret-with-enough-length-for-local-tests",
    ) == {"tokenstore": "plain-garmin-tokenstore"}


def test_structured_logging_redacts_sensitive_fields() -> None:
    payload = {
        "event": "garmin_connection_failed",
        "password": "garmin-password",
        "nested": {
            "session_material": {"ciphertext": "encrypted-session"},
            "safe_count": 3,
        },
        "records": [{"api_key": "openai-key"}],
    }

    assert redact_sensitive_data(payload) == {
        "event": "garmin_connection_failed",
        "password": "[redacted]",
        "nested": {
            "session_material": "[redacted]",
            "safe_count": 3,
        },
        "records": [{"api_key": "[redacted]"}],
    }


def test_structured_logging_preserves_tuple_args() -> None:
    redacted = redact_sensitive_data(("POST", {"token": "session-token"}))

    assert isinstance(redacted, tuple)
    assert redacted == ("POST", {"token": "[redacted]"})


def test_json_log_formatter_redacts_extra_sensitive_fields() -> None:
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="connection event",
        args=(),
        exc_info=None,
    )
    record.__dict__["tokenstore"] = "plain-garmin-tokenstore"
    record.__dict__["safe_count"] = 2

    SensitiveDataFilter().filter(record)
    rendered = formatter.format(record)
    parsed = json.loads(rendered)

    assert "plain-garmin-tokenstore" not in rendered
    assert parsed["extra"]["tokenstore"] == "[redacted]"
    assert parsed["extra"]["safe_count"] == 2


def test_garmin_connection_response_does_not_serialize_session_material() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = AppUser(
        better_auth_user_id="better-auth-user-1",
        email="runner@example.com",
        display_name="Runner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    seen_credentials: list[GarminCredentials] = []

    def client_builder(
        credentials: GarminCredentials,
        _prompt_mfa: Callable[[], str] | None,
        _is_cn: bool,
    ) -> FakeGarminClient:
        seen_credentials.append(credentials)
        return FakeGarminClient(credentials)

    service = GarminConnectionService(
        GarminConnectionSettings(encryption_secret="test-secret-with-enough-length-for-local-tests"),
        client_builder=client_builder,
    )

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_app_user] = lambda: user
    app.dependency_overrides[get_garmin_connection_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/connections/garmin",
            json={
                "username": "runner@example.com",
                "password": "garmin-password",
                "mfa_code": "123456",
            },
        )
        connection = db.scalar(select(SourceConnection))
    finally:
        db.close()

    assert response.status_code == 200
    rendered_response = response.text
    assert "garmin-password" not in rendered_response
    assert "123456" not in rendered_response
    assert "plain-garmin-tokenstore" not in rendered_response
    assert "session_material" not in rendered_response
    assert seen_credentials[0].password == "garmin-password"

    assert connection is not None
    rendered_metadata = json.dumps(connection.connection_metadata)
    assert "plain-garmin-tokenstore" not in rendered_metadata
    assert "garmin-password" not in rendered_metadata
