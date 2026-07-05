from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_app_user
from app.core.security import (
    BETTER_AUTH_SESSION_COOKIE_NAME,
    create_better_auth_session_cookie_value,
)
from app.db.models import Base
from app.db.session import get_db
from app.models import Activity, AppUser, SourceConnection

AUTH_SECRET = "test-secret-with-enough-length-for-local-tests"


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

    @router.get("/activities/{activity_id}")
    def get_activity(
        activity_id: UUID,
        current_user: Annotated[AppUser, Depends(get_current_app_user)],
        route_db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, str]:
        activity = route_db.scalar(
            select(Activity).where(
                Activity.id == activity_id,
                Activity.user_id == current_user.id,
            )
        )
        if activity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Activity not found",
            )

        return {
            "id": str(activity.id),
            "user_id": str(activity.user_id),
            "name": activity.name or "",
        }

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app), db


def _insert_better_auth_session(
    db: Session,
    *,
    user_id: str,
    token: str,
    email: str,
    name: str,
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
            "id": f"{user_id}-session",
            "token": token,
            "user_id": user_id,
            "expires_at": now + timedelta(days=1),
            "created_at": now,
            "updated_at": now,
        },
    )
    db.commit()


def _signed_session_cookie(token: str) -> str:
    signed_cookie = quote(create_better_auth_session_cookie_value(token, AUTH_SECRET))
    return f"{BETTER_AUTH_SESSION_COOKIE_NAME}={signed_cookie}"


def _seed_activity(db: Session, app_user: AppUser, *, source_activity_id: str) -> Activity:
    source_connection = SourceConnection(
        user_id=app_user.id,
        source="garmin",
        status="active",
        provider_subject_id=f"provider-{source_activity_id}",
        display_name="Garmin",
    )
    activity = Activity(
        user_id=app_user.id,
        source_connection=source_connection,
        source_activity_id=source_activity_id,
        activity_type="run",
        name=f"Run {source_activity_id}",
        activity_date=date(2026, 7, 5),
        started_at=datetime(2026, 7, 5, 8, 0, tzinfo=UTC),
        duration_seconds=1800,
        raw_data={"sourceActivityId": source_activity_id},
    )
    db.add_all([source_connection, activity])
    db.commit()
    db.refresh(activity)
    return activity


def _bootstrap_user(db: Session, *, user_id: str, token: str, email: str) -> AppUser:
    _insert_better_auth_session(
        db,
        user_id=user_id,
        token=token,
        email=email,
        name=user_id,
    )
    app_user = AppUser(
        better_auth_user_id=user_id,
        email=email,
        display_name=user_id,
    )
    db.add(app_user)
    db.commit()
    db.refresh(app_user)
    return app_user


def test_unauthenticated_api_request_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("BETTER_AUTH_SECRET", AUTH_SECRET)
    client, db = _create_test_client()

    try:
        response = client.get("/activities/00000000-0000-0000-0000-000000000000")
    finally:
        db.close()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Authentication required"}


def test_authenticated_user_can_access_own_record(monkeypatch) -> None:
    monkeypatch.setenv("BETTER_AUTH_SECRET", AUTH_SECRET)
    client, db = _create_test_client()
    app_user = _bootstrap_user(
        db,
        user_id="better-auth-user-1",
        token="session-token-1",
        email="runner@example.com",
    )
    activity = _seed_activity(db, app_user, source_activity_id="activity-1")
    app_user_id = app_user.id
    activity_id = activity.id

    try:
        response = client.get(
            f"/activities/{activity_id}",
            headers={"cookie": _signed_session_cookie("session-token-1")},
        )
    finally:
        db.close()

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": str(activity_id),
        "user_id": str(app_user_id),
        "name": "Run activity-1",
    }


def test_authenticated_user_cannot_access_another_users_record(monkeypatch) -> None:
    monkeypatch.setenv("BETTER_AUTH_SECRET", AUTH_SECRET)
    client, db = _create_test_client()
    owner = _bootstrap_user(
        db,
        user_id="better-auth-user-1",
        token="session-token-1",
        email="owner@example.com",
    )
    requester = _bootstrap_user(
        db,
        user_id="better-auth-user-2",
        token="session-token-2",
        email="requester@example.com",
    )
    activity = _seed_activity(db, owner, source_activity_id="activity-1")
    owner_id = owner.id
    requester_id = requester.id
    activity_id = activity.id

    try:
        response = client.get(
            f"/activities/{activity_id}",
            headers={"cookie": _signed_session_cookie("session-token-2")},
        )
    finally:
        db.close()

    assert requester_id != owner_id
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Activity not found"}
