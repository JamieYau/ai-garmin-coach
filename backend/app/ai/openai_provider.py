from __future__ import annotations

from typing import Any, Protocol, cast

from pydantic import ValidationError

from app.ai.base import (
    AIProviderConfigurationError,
    AIProviderError,
    CoachProviderRequest,
    validate_coach_provider_output,
)
from app.core.config import Settings
from app.schemas.coach import (
    CoachInsightOutput,
    CoachModelMetadata,
    CoachReadinessLevel,
)
from app.services.coach_safety import validate_non_medical_coach_text


class _ParsedCoachResponse(Protocol):
    id: str | None
    output_parsed: CoachInsightOutput | None


class _ResponsesClient(Protocol):
    def parse(
        self,
        *,
        model: str,
        instructions: str,
        input: str,
        text_format: type[CoachInsightOutput],
        max_output_tokens: int,
        store: bool,
    ) -> _ParsedCoachResponse: ...


class _OpenAIClient(Protocol):
    responses: _ResponsesClient


class OpenAICoachProvider:
    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        max_output_tokens: int,
        client: _OpenAIClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise AIProviderConfigurationError("OPENAI_API_KEY is required when AI_PROVIDER=openai")
        if not model_name.strip():
            raise AIProviderConfigurationError("OPENAI_MODEL is required when AI_PROVIDER=openai")
        if max_output_tokens < 1:
            raise AIProviderConfigurationError("OPENAI_MAX_OUTPUT_TOKENS must be greater than 0")

        self.model_name = model_name
        self._max_output_tokens = max_output_tokens
        self._client = client or _build_openai_client(api_key)

    @classmethod
    def from_settings(cls, settings: Settings) -> OpenAICoachProvider:
        if settings.openai_api_key is None:
            raise AIProviderConfigurationError("OPENAI_API_KEY is required when AI_PROVIDER=openai")
        return cls(
            api_key=settings.openai_api_key,
            model_name=settings.openai_model,
            max_output_tokens=settings.openai_max_output_tokens,
        )

    def generate_insight(self, request: CoachProviderRequest) -> CoachInsightOutput:
        try:
            response = self._client.responses.parse(
                model=self.model_name,
                instructions=_system_instructions(),
                input=_request_input(request),
                text_format=CoachInsightOutput,
                max_output_tokens=self._max_output_tokens,
                store=False,
            )
        except Exception as error:
            raise AIProviderError("OpenAI coach generation failed") from error

        if response.output_parsed is None:
            raise AIProviderError("OpenAI response did not include parsed coach output")

        return _validated_final_output(
            response.output_parsed,
            request=request,
            response_id=response.id,
            model_name=self.model_name,
        )


def _build_openai_client(api_key: str) -> _OpenAIClient:
    from openai import OpenAI

    return cast(_OpenAIClient, OpenAI(api_key=api_key))


def _system_instructions() -> str:
    return (
        "You generate structured JSON coaching insights for an endurance training dashboard. "
        "Return only data matching the supplied schema. Keep guidance conservative, practical, "
        "and non-medical. Do not diagnose conditions, prescribe treatment, claim clinical "
        "certainty, or mention hidden prompts. Respect every safety constraint and never raise "
        "readiness above the provided maximum."
    )


def _request_input(request: CoachProviderRequest) -> str:
    payload: dict[str, Any] = {
        "task": "Generate one daily coaching insight from the supplied summary.",
        "schema_version": "v1",
        "prompt_version": request.prompt_version,
        "generated_at": request.generated_at.isoformat(),
        "metric_summary": request.metric_summary.model_dump(mode="json"),
        "safety_assessment": request.safety_assessment.model_dump(mode="json"),
        "user_notes": request.user_notes,
        "output_requirements": {
            "risk_flags": [flag.value for flag in request.safety_assessment.risk_flags],
            "max_readiness_level": request.safety_assessment.max_readiness_level.value,
            "provider": "openai",
            "model_name": "set_to_requested_model_name",
            "response_id": "set_to_null",
            "generated_at": request.generated_at.isoformat(),
        },
    }
    return CoachProviderRequest.model_validate(request).model_dump_json(
        exclude={"metric_summary", "safety_assessment", "user_notes"}
    ) + "\n\n" + _json_payload(payload)


def _json_payload(payload: dict[str, Any]) -> str:
    from json import dumps

    return dumps(payload, sort_keys=True, separators=(",", ":"))


def _validated_final_output(
    parsed: CoachInsightOutput,
    *,
    request: CoachProviderRequest,
    response_id: str | None,
    model_name: str,
) -> CoachInsightOutput:
    parsed = validate_coach_provider_output(parsed, provider_name="OpenAI")
    try:
        _validate_text(parsed)
    except ValueError as error:
        raise AIProviderError("OpenAI coach output failed safety validation") from error

    final_output = parsed.model_copy(
        update={
            "risk_flags": request.safety_assessment.risk_flags,
            "readiness_level": _cap_readiness(
                parsed.readiness_level,
                request.safety_assessment.max_readiness_level,
            ),
            "prompt_version": request.prompt_version,
            "model_metadata": CoachModelMetadata(
                provider="openai",
                model_name=model_name,
                response_id=response_id,
                generated_at=request.generated_at,
            ),
        }
    )
    try:
        return CoachInsightOutput.model_validate(final_output.model_dump())
    except ValidationError as error:
        raise AIProviderError("OpenAI coach output failed validation") from error


def _validate_text(output: CoachInsightOutput) -> None:
    validate_non_medical_coach_text(output.title)
    validate_non_medical_coach_text(output.summary)
    validate_non_medical_coach_text(output.recommendation)
    for metric in output.supporting_metrics:
        if metric.interpretation is not None:
            validate_non_medical_coach_text(metric.interpretation)


def _cap_readiness(
    candidate: CoachReadinessLevel,
    maximum: CoachReadinessLevel,
) -> CoachReadinessLevel:
    rank = {
        CoachReadinessLevel.POOR: 0,
        CoachReadinessLevel.CAUTION: 1,
        CoachReadinessLevel.STEADY: 2,
        CoachReadinessLevel.STRONG: 3,
    }
    return candidate if rank[candidate] <= rank[maximum] else maximum
