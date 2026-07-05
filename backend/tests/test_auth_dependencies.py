from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_app_user
from app.core.security import (
    BETTER_AUTH_SESSION_COOKIE_NAME,
    create_better_auth_session_cookie_value,
)
from app.db.models import Base
from app.db.session import get_db
from app.models import AppUser


def _create_test_client() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE "user" (
                    "id" VARCHAR PRIMARY KEY,
                    "name" VARCHAR NOT NULL,
                    "email" VARCHAR NOT NULL,
                    "emailVerified" BOOLEAN NOT NULL,
                    "createdAt" DATETIME NOT NULL,
                    "updatedAt" DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE "session" (
                    "id" VARCHAR PRIMARY KEY,
                    "token" VARCHAR NOT NULL UNIQUE,
                    "userId" VARCHAR NOT NULL,
                    "expiresAt" DATETIME NOT NULL,
                    "createdAt" DATETIME NOT NULL,
                    "updatedAt" DATETIME NOT NULL,
                    FOREIGN KEY("userId") REFERENCES "user"("id")
                )
                """
            )
        )

    db = Session(engine)

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    router = APIRouter()

    @router.get("/protected/me")
    def protected_me(
        current_user: Annotated[AppUser, Depends(get_current_app_user)],
    ) -> dict[str, str]:
        return {
            "id": str(current_user.id),
            "better_auth_user_id": current_user.better_auth_user_id,
            "email": current_user.email,
            "display_name": current_user.display_name or "",
        }

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app), db


def _insert_better_auth_session(
    db: Session,
    *,
    user_id: str = "better-auth-user-1",
    token: str = "session-token-1",
    email: str = "runner@example.com",
    name: str = "Runner",
    expires_at: datetime | None = None,
) -> None:
    now = datetime.now(UTC)
    db.execute(
        text(
            """
            INSERT INTO "user" ("id", "name", "email", "emailVerified", "createdAt", "updatedAt")
            VALUES (:id, :name, :email, :email_verified, :created_at, :updated_at)
            """
        ),
        {
            "id": user_id,
            "name": name,
            "email": email,
            "email_verified": True,
            "created_at": now,
            "updated_at": now,
        },
    )
    db.execute(
        text(
            """
            INSERT INTO "session" ("id", "token", "userId", "expiresAt", "createdAt", "updatedAt")
            VALUES (:id, :token, :user_id, :expires_at, :created_at, :updated_at)
            """
        ),
        {
            "id": "better-auth-session-1",
            "token": token,
            "user_id": user_id,
            "expires_at": expires_at or now + timedelta(days=1),
            "created_at": now,
            "updated_at": now,
        },
    )
    db.commit()


def test_protected_dependency_rejects_missing_session(monkeypatch) -> None:
    monkeypatch.setenv("BETTER_AUTH_SECRET", "test-secret-with-enough-length-for-local-tests")
    client, db = _create_test_client()

    try:
        response = client.get("/protected/me")
    finally:
        db.close()

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_protected_dependency_maps_valid_better_auth_cookie_to_app_user(monkeypatch) -> None:
    secret = "test-secret-with-enough-length-for-local-tests"
    monkeypatch.setenv("BETTER_AUTH_SECRET", secret)
    client, db = _create_test_client()
    _insert_better_auth_session(db)
    signed_cookie = quote(create_better_auth_session_cookie_value("session-token-1", secret))

    try:
        response = client.get(
            "/protected/me",
            headers={"cookie": f"{BETTER_AUTH_SESSION_COOKIE_NAME}={signed_cookie}"},
        )
    finally:
        db.close()

    assert response.status_code == 200
    assert response.json()["better_auth_user_id"] == "better-auth-user-1"
    assert response.json()["email"] == "runner@example.com"
    assert response.json()["display_name"] == "Runner"


def test_protected_dependency_updates_existing_app_user_from_better_auth(monkeypatch) -> None:
    monkeypatch.setenv("BETTER_AUTH_SECRET", "test-secret-with-enough-length-for-local-tests")
    client, db = _create_test_client()
    _insert_better_auth_session(
        db,
        token="session-token-2",
        email="updated@example.com",
        name="Updated Runner",
    )
    db.add(
        AppUser(
            better_auth_user_id="better-auth-user-1",
            email="old@example.com",
            display_name="Old Runner",
        )
    )
    db.commit()

    try:
        response = client.get(
            "/protected/me",
            headers={"authorization": "Bearer session-token-2"},
        )
    finally:
        db.close()

    assert response.status_code == 200
    assert response.json()["email"] == "updated@example.com"
    assert response.json()["display_name"] == "Updated Runner"


def test_protected_dependency_rejects_expired_session(monkeypatch) -> None:
    monkeypatch.setenv("BETTER_AUTH_SECRET", "test-secret-with-enough-length-for-local-tests")
    client, db = _create_test_client()
    _insert_better_auth_session(
        db,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    try:
        response = client.get(
            "/protected/me",
            headers={"authorization": "Bearer session-token-1"},
        )
    finally:
        db.close()

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired session"}
