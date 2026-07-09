from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.coach import CoachReadinessLevel, CoachRiskFlag
from app.services.metric_summary import CoachMetricSummary


class CoachSafetyError(ValueError):
    pass


class CoachRecommendationMode(StrEnum):
    NORMAL = "normal"
    CONSERVATIVE = "conservative"
    REST_OR_EASY = "rest_or_easy"


class CoachSafetyAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    risk_flags: list[CoachRiskFlag] = Field(default_factory=list)
    recommendation_mode: CoachRecommendationMode = CoachRecommendationMode.NORMAL
    max_readiness_level: CoachReadinessLevel = CoachReadinessLevel.STRONG
    prompt_constraints: list[str] = Field(default_factory=list)
    user_note_flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_flags(self) -> CoachSafetyAssessment:
        if len(set(self.risk_flags)) != len(self.risk_flags):
            raise ValueError("risk_flags must not contain duplicates")
        return self


_INJURY_OR_PAIN_PATTERN = re.compile(
    r"\b("
    r"ache|aches|aching|"
    r"hurt|hurts|hurting|"
    r"injured|injury|"
    r"niggle|pain|painful|"
    r"strain|strained|"
    r"sore|soreness|"
    r"swollen|swelling"
    r")\b",
    re.IGNORECASE,
)

_MEDICAL_DIAGNOSIS_PATTERNS = (
    re.compile(r"\bdiagnos(?:e|ed|es|ing|is)\b", re.IGNORECASE),
    re.compile(r"\byou have\b", re.IGNORECASE),
    re.compile(r"\bthis is (?:a|an)\b", re.IGNORECASE),
    re.compile(r"\bprescrib(?:e|ed|es|ing)\b", re.IGNORECASE),
    re.compile(r"\btreat(?:ment)? plan\b", re.IGNORECASE),
    re.compile(r"\bmedical condition\b", re.IGNORECASE),
)


def assess_coach_safety(
    metric_summary: CoachMetricSummary,
    *,
    user_notes: list[str] | None = None,
) -> CoachSafetyAssessment:
    risk_flags: list[CoachRiskFlag] = []
    prompt_constraints = [
        "Keep coaching guidance conservative and non-medical.",
        "Do not diagnose conditions, prescribe treatment, or claim clinical certainty.",
    ]
    user_note_flags: list[str] = []
    recommendation_mode = CoachRecommendationMode.NORMAL
    max_readiness_level = CoachReadinessLevel.STRONG

    if _has_data_gap(metric_summary):
        risk_flags.append(CoachRiskFlag.DATA_GAP)
        prompt_constraints.append(
            "Call out missing or sparse data before making firm recommendations."
        )
        recommendation_mode = _more_conservative(
            recommendation_mode,
            CoachRecommendationMode.CONSERVATIVE,
        )
        max_readiness_level = _lower_readiness(max_readiness_level, CoachReadinessLevel.STEADY)

    if _has_sleep_deficit(metric_summary):
        risk_flags.append(CoachRiskFlag.SLEEP_DEFICIT)
        prompt_constraints.append("Prioritize sleep and recovery before adding intensity.")
        recommendation_mode = _more_conservative(
            recommendation_mode,
            CoachRecommendationMode.CONSERVATIVE,
        )
        max_readiness_level = _lower_readiness(max_readiness_level, CoachReadinessLevel.CAUTION)

    if _has_poor_recovery(metric_summary):
        risk_flags.append(CoachRiskFlag.POOR_RECOVERY)
        prompt_constraints.append("Recommend rest, mobility, or easy aerobic work only.")
        recommendation_mode = _more_conservative(
            recommendation_mode,
            CoachRecommendationMode.REST_OR_EASY,
        )
        max_readiness_level = _lower_readiness(max_readiness_level, CoachReadinessLevel.CAUTION)

    if metric_summary.recovery.resting_heart_rate_trend == "up":
        risk_flags.append(CoachRiskFlag.ELEVATED_RESTING_HEART_RATE)
        prompt_constraints.append(
            "Mention elevated resting heart rate as a caution signal, not a diagnosis."
        )
        recommendation_mode = _more_conservative(
            recommendation_mode,
            CoachRecommendationMode.CONSERVATIVE,
        )

    if metric_summary.recovery.hrv_trend == "down":
        risk_flags.append(CoachRiskFlag.LOW_HRV)
        prompt_constraints.append("Mention lower HRV as a recovery signal, not a medical finding.")
        recommendation_mode = _more_conservative(
            recommendation_mode,
            CoachRecommendationMode.CONSERVATIVE,
        )

    if metric_summary.activity.duration_trend == "up":
        risk_flags.append(CoachRiskFlag.HIGH_TRAINING_LOAD)
        prompt_constraints.append("Avoid recommending another hard session after a load increase.")

    if _notes_include_injury_or_pain(user_notes or []):
        risk_flags.append(CoachRiskFlag.INJURY_OR_PAIN)
        user_note_flags.append("injury_or_pain_language")
        prompt_constraints.append(
            "If pain or injury is mentioned, recommend stopping hard training and seeking "
            "qualified help if symptoms persist."
        )
        recommendation_mode = _more_conservative(
            recommendation_mode,
            CoachRecommendationMode.REST_OR_EASY,
        )
        max_readiness_level = _lower_readiness(max_readiness_level, CoachReadinessLevel.CAUTION)

    return CoachSafetyAssessment(
        risk_flags=_dedupe_flags(risk_flags),
        recommendation_mode=recommendation_mode,
        max_readiness_level=max_readiness_level,
        prompt_constraints=prompt_constraints,
        user_note_flags=user_note_flags,
    )


def validate_non_medical_coach_text(text: str) -> None:
    for pattern in _MEDICAL_DIAGNOSIS_PATTERNS:
        if pattern.search(text):
            raise CoachSafetyError("coach text contains medical diagnosis or treatment language")


def _has_data_gap(metric_summary: CoachMetricSummary) -> bool:
    return (
        metric_summary.activity.activity_count == 0
        or metric_summary.sleep.nights_recorded < 3
        or metric_summary.recovery.days_recorded < 3
    )


def _has_sleep_deficit(metric_summary: CoachMetricSummary) -> bool:
    average_sleep = metric_summary.sleep.average_sleep_seconds
    average_score = metric_summary.sleep.average_sleep_score
    return (
        average_sleep is not None
        and average_sleep < 6 * 60 * 60
        or average_score is not None
        and average_score < 60
    )


def _has_poor_recovery(metric_summary: CoachMetricSummary) -> bool:
    return (
        metric_summary.recovery.hrv_trend == "down"
        and metric_summary.recovery.resting_heart_rate_trend == "up"
    )


def _notes_include_injury_or_pain(notes: list[str]) -> bool:
    return any(_INJURY_OR_PAIN_PATTERN.search(note) for note in notes)


def _dedupe_flags(risk_flags: list[CoachRiskFlag]) -> list[CoachRiskFlag]:
    seen: set[CoachRiskFlag] = set()
    deduped: list[CoachRiskFlag] = []
    for risk_flag in risk_flags:
        if risk_flag not in seen:
            deduped.append(risk_flag)
            seen.add(risk_flag)
    return deduped


def _more_conservative(
    current: CoachRecommendationMode,
    candidate: CoachRecommendationMode,
) -> CoachRecommendationMode:
    rank = {
        CoachRecommendationMode.NORMAL: 0,
        CoachRecommendationMode.CONSERVATIVE: 1,
        CoachRecommendationMode.REST_OR_EASY: 2,
    }
    return candidate if rank[candidate] > rank[current] else current


def _lower_readiness(
    current: CoachReadinessLevel,
    candidate: CoachReadinessLevel,
) -> CoachReadinessLevel:
    rank = {
        CoachReadinessLevel.POOR: 0,
        CoachReadinessLevel.CAUTION: 1,
        CoachReadinessLevel.STEADY: 2,
        CoachReadinessLevel.STRONG: 3,
    }
    return candidate if rank[candidate] < rank[current] else current
