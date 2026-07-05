from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_app_user
from app.connectors.garmin.connection import (
    GarminAuthenticationError,
    GarminConnectionError,
    GarminConnectionService,
    GarminConnectionSettings,
    GarminRateLimitError,
)
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import AppUser
from app.schemas.connections import ConnectionResponse, GarminConnectionCreate

router = APIRouter(prefix="/connections", tags=["connections"])


def get_garmin_connection_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GarminConnectionService:
    if not settings.better_auth_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Connection encryption is not configured",
        )
    return GarminConnectionService(
        GarminConnectionSettings(encryption_secret=settings.better_auth_secret)
    )


@router.post("/garmin", response_model=ConnectionResponse)
def connect_garmin(
    request: GarminConnectionCreate,
    current_user: Annotated[AppUser, Depends(get_current_app_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[GarminConnectionService, Depends(get_garmin_connection_service)],
) -> ConnectionResponse:
    try:
        return service.setup_connection(db, current_user, request)
    except GarminAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Garmin authentication failed",
        ) from exc
    except GarminRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Garmin rate limit exceeded",
        ) from exc
    except GarminConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Garmin connection failed",
        ) from exc
