from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_app_user
from app.db.session import get_db
from app.models import AppUser
from app.services.data_lifecycle import (
    DeleteAccountDataResult,
    DeleteSyncedDataResult,
    SourceConnectionNotFoundError,
    UnsupportedDataSourceError,
    delete_account_data,
    delete_synced_data,
)

router = APIRouter(prefix="/users", tags=["users"])


class DeleteSyncedDataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str | None
    activities_deleted: int
    daily_metrics_deleted: int
    sleep_sessions_deleted: int
    biometric_samples_deleted: int
    raw_observations_deleted: int
    sync_runs_deleted: int
    coach_insights_deleted: int
    total_deleted: int

    @classmethod
    def from_result(cls, result: DeleteSyncedDataResult) -> DeleteSyncedDataResponse:
        return cls(
            source=result.source,
            activities_deleted=result.activities_deleted,
            daily_metrics_deleted=result.daily_metrics_deleted,
            sleep_sessions_deleted=result.sleep_sessions_deleted,
            biometric_samples_deleted=result.biometric_samples_deleted,
            raw_observations_deleted=result.raw_observations_deleted,
            sync_runs_deleted=result.sync_runs_deleted,
            coach_insights_deleted=result.coach_insights_deleted,
            total_deleted=result.total_deleted,
        )


class DeleteAccountDataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str
    deleted: bool
    source_connections_deleted: int
    synced_records_deleted: int
    total_deleted: int

    @classmethod
    def from_result(cls, result: DeleteAccountDataResult) -> DeleteAccountDataResponse:
        return cls(
            user_id=str(result.user_id),
            deleted=result.deleted,
            source_connections_deleted=result.source_connections_deleted,
            synced_records_deleted=result.synced_data.total_deleted,
            total_deleted=result.total_deleted,
        )


@router.delete("/me/data", response_model=DeleteSyncedDataResponse)
def delete_current_user_synced_data(
    current_user: Annotated[AppUser, Depends(get_current_app_user)],
    db: Annotated[Session, Depends(get_db)],
    source: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
) -> DeleteSyncedDataResponse:
    try:
        result = delete_synced_data(db, current_user, source=source)
    except UnsupportedDataSourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported source",
        ) from exc
    except SourceConnectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source connection not found",
        ) from exc
    return DeleteSyncedDataResponse.from_result(result)


@router.delete("/me", response_model=DeleteAccountDataResponse)
def delete_current_user_account_data(
    current_user: Annotated[AppUser, Depends(get_current_app_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DeleteAccountDataResponse:
    return DeleteAccountDataResponse.from_result(delete_account_data(db, current_user))
