from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.connections import get_garmin_connection_service
from app.api.dependencies import get_current_app_user
from app.db.models import Base
from app.db.session import get_db
from app.main import create_app
from app.models import AppUser
from app.schemas.connections import ConnectionResponse, GarminConnectionCreate


class FakeGarminConnectionService:
    def __init__(self, response: ConnectionResponse) -> None:
        self.response = response
        self.seen_request: GarminConnectionCreate | None = None

    def setup_connection(
        self,
        db: Session,
        user: AppUser,
        request: GarminConnectionCreate,
    ) -> ConnectionResponse:
        self.seen_request = request
        assert user.email == "runner@example.com"
        return self.response


def _create_client(
    service: FakeGarminConnectionService,
) -> tuple[TestClient, Session, AppUser]:
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

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_app_user] = lambda: user
    app.dependency_overrides[get_garmin_connection_service] = lambda: service
    return TestClient(app), db, user


def test_connect_garmin_returns_active_connection_without_secrets() -> None:
    service = FakeGarminConnectionService(
        ConnectionResponse(
            id="00000000-0000-0000-0000-000000000001",
            source="garmin",
            status="active",
            provider_subject_id="123",
            display_name="Runner Example",
        )
    )
    client, db, _user = _create_client(service)

    try:
        response = client.post(
            "/connections/garmin",
            json={
                "username": "runner@example.com",
                "password": "garmin-password",
            },
        )
    finally:
        db.close()

    assert response.status_code == 200
    assert response.json() == {
        "id": "00000000-0000-0000-0000-000000000001",
        "source": "garmin",
        "status": "active",
        "provider_subject_id": "123",
        "display_name": "Runner Example",
        "requires_mfa": False,
        "message": None,
    }
    assert service.seen_request is not None
    assert "garmin-password" not in repr(service.seen_request)


def test_connect_garmin_can_return_mfa_required_state() -> None:
    service = FakeGarminConnectionService(
        ConnectionResponse(
            source="garmin",
            status="mfa_required",
            requires_mfa=True,
            message="Garmin requires a multi-factor authentication code.",
        )
    )
    client, db, _user = _create_client(service)

    try:
        response = client.post(
            "/connections/garmin",
            json={
                "username": "runner@example.com",
                "password": "garmin-password",
            },
        )
    finally:
        db.close()

    assert response.status_code == 200
    assert response.json()["status"] == "mfa_required"
    assert response.json()["requires_mfa"] is True
    assert response.json()["id"] is None
