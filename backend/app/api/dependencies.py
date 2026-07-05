from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import get_better_auth_session_token
from app.db.session import get_db
from app.models import AppUser


@dataclass(frozen=True)
class BetterAuthIdentity:
    user_id: str
    email: str
    display_name: str | None
    session_expires_at: datetime


@dataclass(frozen=True)
class AuthenticatedUser:
    app_user: AppUser
    better_auth: BetterAuthIdentity


def _coerce_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise TypeError("Unsupported datetime value from Better Auth session")

    if result.tzinfo is None:
        return result.replace(tzinfo=UTC)
    return result.astimezone(UTC)


def _load_better_auth_identity(db: Session, token: str) -> BetterAuthIdentity | None:
    row = db.execute(
        text(
            """
            SELECT
                ba_session."userId" AS user_id,
                ba_session."expiresAt" AS expires_at,
                ba_user."email" AS email,
                ba_user."name" AS display_name
            FROM "session" AS ba_session
            JOIN "user" AS ba_user ON ba_user."id" = ba_session."userId"
            WHERE ba_session."token" = :token
            """
        ),
        {"token": token},
    ).mappings().first()
    if row is None:
        return None

    expires_at = _coerce_datetime(row["expires_at"])
    if expires_at <= datetime.now(UTC):
        return None

    return BetterAuthIdentity(
        user_id=str(row["user_id"]),
        email=str(row["email"]),
        display_name=str(row["display_name"]) if row["display_name"] is not None else None,
        session_expires_at=expires_at,
    )


def _get_or_create_app_user(db: Session, identity: BetterAuthIdentity) -> AppUser:
    app_user = db.scalar(
        select(AppUser).where(AppUser.better_auth_user_id == identity.user_id)
    )
    if app_user is None:
        app_user = AppUser(
            better_auth_user_id=identity.user_id,
            email=identity.email,
            display_name=identity.display_name,
        )
        db.add(app_user)
    else:
        app_user.update_from_better_auth(
            email=identity.email,
            display_name=identity.display_name,
        )

    db.commit()
    db.refresh(app_user)
    return app_user


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    if not settings.better_auth_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured",
        )

    token = get_better_auth_session_token(request, settings.better_auth_secret)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    identity = _load_better_auth_identity(db, token)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    return AuthenticatedUser(
        app_user=_get_or_create_app_user(db, identity),
        better_auth=identity,
    )


def get_current_app_user(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AppUser:
    return current_user.app_user
