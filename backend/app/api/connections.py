from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
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
from app.schemas.sync import ManualSyncResponse
from app.services.data_lifecycle import (
    DisconnectSourceResult,
    SourceConnectionNotFoundError,
    disconnect_source,
)
from app.services.demo_data import DemoDataService

router = APIRouter(prefix="/connections", tags=["connections"])


class DisconnectSourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    source: str
    status: str

    @classmethod
    def from_result(cls, result: DisconnectSourceResult) -> DisconnectSourceResponse:
        return cls(
            id=str(result.source_connection_id),
            source=result.source,
            status=result.status,
        )


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


def get_demo_data_service() -> DemoDataService:
    return DemoDataService()


@router.post("/demo", response_model=ManualSyncResponse)
async def load_demo_data(
    current_user: Annotated[AppUser, Depends(get_current_app_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[DemoDataService, Depends(get_demo_data_service)],
) -> ManualSyncResponse:
    """Load synthetic dashboard records without collecting Garmin credentials."""
    sync_run = await service.load_dashboard_data(db, current_user)
    return ManualSyncResponse.model_validate(sync_run)


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


@router.delete("/garmin", response_model=DisconnectSourceResponse)
def disconnect_garmin(
    current_user: Annotated[AppUser, Depends(get_current_app_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DisconnectSourceResponse:
    try:
        result = disconnect_source(db, current_user, source="garmin")
    except SourceConnectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source connection not found",
        ) from exc
    return DisconnectSourceResponse.from_result(result)
