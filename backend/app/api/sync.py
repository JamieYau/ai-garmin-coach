from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_app_user
from app.connectors.garmin.sync import GarminActivitySyncService
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import AppUser
from app.schemas.sync import ManualSyncRequest, ManualSyncResponse
from app.services.sync import (
    ManualSyncService,
    ManualSyncWindowError,
    SourceConnectionNotActiveError,
    SourceConnectionNotFoundError,
    SyncAlreadyRunningError,
    UnsupportedSyncSourceError,
)

router = APIRouter(prefix="/sync", tags=["sync"])


def get_manual_sync_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ManualSyncService:
    if not settings.better_auth_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sync encryption is not configured",
        )
    return ManualSyncService(
        GarminActivitySyncService(encryption_secret=settings.better_auth_secret)
    )


@router.post("/manual", response_model=ManualSyncResponse)
def trigger_manual_sync(
    request: ManualSyncRequest,
    current_user: Annotated[AppUser, Depends(get_current_app_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[ManualSyncService, Depends(get_manual_sync_service)],
) -> ManualSyncResponse:
    try:
        sync_run = service.trigger_manual_sync(db, current_user, request)
    except UnsupportedSyncSourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported sync source",
        ) from exc
    except SourceConnectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source connection not found",
        ) from exc
    except SourceConnectionNotActiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Source connection is not active",
        ) from exc
    except SyncAlreadyRunningError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A sync is already queued or running",
        ) from exc
    except ManualSyncWindowError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ManualSyncResponse.model_validate(sync_run)
