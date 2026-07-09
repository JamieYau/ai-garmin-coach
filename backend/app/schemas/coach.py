from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

COACH_INSIGHT_SCHEMA_VERSION: Literal["v1"] = "v1"


class CoachReadinessLevel(StrEnum):
    POOR = "poor"
    CAUTION = "caution"
    STEADY = "steady"
    STRONG = "strong"


class CoachRiskFlag(StrEnum):
    DATA_GAP = "data_gap"
    ELEVATED_RESTING_HEART_RATE = "elevated_resting_heart_rate"
    HIGH_TRAINING_LOAD = "high_training_load"
    INJURY_OR_PAIN = "injury_or_pain"
    LOW_HRV = "low_hrv"
    POOR_RECOVERY = "poor_recovery"
    SLEEP_DEFICIT = "sleep_deficit"


class CoachMetricTrend(StrEnum):
    DOWN = "down"
    FLAT = "flat"
    MIXED = "mixed"
    UP = "up"
    UNKNOWN = "unknown"


class CoachSupportingMetric(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=100)
    value: int | Decimal | str | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    period: str = Field(min_length=1, max_length=64)
    trend: CoachMetricTrend = CoachMetricTrend.UNKNOWN
    interpretation: str | None = Field(default=None, min_length=1, max_length=300)


class CoachModelMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1, max_length=64)
    model_name: str = Field(min_length=1, max_length=128)
    response_id: str | None = Field(default=None, min_length=1, max_length=255)
    generated_at: datetime


class CoachInsightOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["v1"] = COACH_INSIGHT_SCHEMA_VERSION
    readiness_level: CoachReadinessLevel
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=1200)
    recommendation: str = Field(min_length=1, max_length=1200)
    supporting_metrics: list[CoachSupportingMetric] = Field(default_factory=list, max_length=20)
    risk_flags: list[CoachRiskFlag] = Field(default_factory=list, max_length=10)
    confidence: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    prompt_version: str = Field(min_length=1, max_length=64)
    model_metadata: CoachModelMetadata

    @model_validator(mode="after")
    def validate_risk_flags(self) -> CoachInsightOutput:
        if len(set(self.risk_flags)) != len(self.risk_flags):
            raise ValueError("risk_flags must not contain duplicates")
        return self
