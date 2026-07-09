from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings, get_settings
from app.schemas.coach import CoachInsightOutput
from app.services.coach_safety import CoachSafetyAssessment
from app.services.metric_summary import CoachMetricSummary


class AIProviderConfigurationError(ValueError):
    pass


class AIProviderError(RuntimeError):
    pass


class CoachProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric_summary: CoachMetricSummary
    safety_assessment: CoachSafetyAssessment
    prompt_version: str = Field(default="daily-v1", min_length=1, max_length=64)
    user_notes: list[str] = Field(default_factory=list, max_length=20)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CoachProvider(Protocol):
    provider_name: str
    model_name: str

    def generate_insight(self, request: CoachProviderRequest) -> CoachInsightOutput:
        """Generate a validated coach insight without exposing raw prompts or provider output."""


def get_coach_provider(settings: Settings | None = None) -> CoachProvider:
    resolved_settings = settings or get_settings()
    provider_name = resolved_settings.ai_provider.strip().lower()

    if provider_name == "mock":
        from app.ai.mock import MockCoachProvider

        return MockCoachProvider()
    if provider_name == "openai":
        from app.ai.openai_provider import OpenAICoachProvider

        return OpenAICoachProvider.from_settings(resolved_settings)

    raise AIProviderConfigurationError(f"Unsupported AI_PROVIDER: {resolved_settings.ai_provider}")
