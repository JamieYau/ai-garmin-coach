from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ManualSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = Field(default="garmin", min_length=1, max_length=64)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_window(self) -> ManualSyncRequest:
        if self.start_date is None and self.end_date is not None:
            raise ValueError("start_date is required when end_date is provided")
        if self.start_date is not None and self.end_date is None:
            raise ValueError("end_date is required when start_date is provided")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must be before or equal to end_date")
        return self


class ManualSyncResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    source_connection_id: uuid.UUID
    status: str
    sync_type: str
    window_start: datetime | None = None
    window_end: datetime | None = None
    records_seen: int
    records_imported: int
    error_code: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
