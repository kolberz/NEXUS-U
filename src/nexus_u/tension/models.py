from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import time
from typing import Any
import uuid


class TensionKind(StrEnum):
    CONTRADICTION = "CONTRADICTION"
    SCOPE_CONFLICT = "SCOPE_CONFLICT"
    CAUSAL_CONFLICT = "CAUSAL_CONFLICT"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    COMPOSITION_FAILURE = "COMPOSITION_FAILURE"
    MODEL_DATA_MISMATCH = "MODEL_DATA_MISMATCH"
    EVIDENCE_GAP = "EVIDENCE_GAP"


class HypothesisKind(StrEnum):
    NARROW_SCOPE = "NARROW_SCOPE"
    CALIBRATION_ERROR = "CALIBRATION_ERROR"
    HIDDEN_VARIABLE = "HIDDEN_VARIABLE"
    MODEL_REVISION = "MODEL_REVISION"
    DEPENDENCY_CORRECTION = "DEPENDENCY_CORRECTION"
    RESOURCE_REGIME = "RESOURCE_REGIME"
    HUMAN_POLICY_DECISION = "HUMAN_POLICY_DECISION"


class DiscoveryStatus(StrEnum):
    NO_TENSION = "NO_TENSION"
    TENSION_DETECTED = "TENSION_DETECTED"
    EXPERIMENT_RECOMMENDED = "EXPERIMENT_RECOMMENDED"
    TENSION_REDUCED = "TENSION_REDUCED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(slots=True)
class Tension:
    obligation_id: str
    statement: str
    kind: TensionKind
    score: float
    support_weight: float
    refute_weight: float
    supporting_evidence: list[str]
    refuting_evidence: list[str]
    organizations: list[str]
    provenance_groups: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    tension_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DiscoveryHypothesis:
    tension_id: str
    description: str
    kind: HypothesisKind
    prior: float = 0.25
    complexity: float = 1.0
    predicted_resolution: float = 0.5
    new_obligations: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    hypothesis_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["discovery_value"] = self.discovery_value
        return raw

    @property
    def discovery_value(self) -> float:
        burden = max(0.1, self.complexity + 0.5 * len(self.new_obligations))
        return round(self.predicted_resolution / burden, 6)


@dataclass(slots=True)
class DiscriminatingExperiment:
    description: str
    outcomes: list[str]
    likelihoods: dict[str, dict[str, float]]
    cost: float = 1.0
    risk: float = 0.0
    prerequisites: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    experiment_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExperimentRecommendation:
    experiment_id: str
    expected_information_gain: float
    utility: float
    expected_outcome_probabilities: dict[str, float]
    rationale: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ObservedExperimentResult:
    experiment_id: str
    outcome: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TensionDiscoveryReport:
    obligation_id: str
    status: DiscoveryStatus
    tensions: list[Tension]
    hypotheses: list[DiscoveryHypothesis]
    experiments: list[DiscriminatingExperiment]
    recommendation: ExperimentRecommendation | None
    prior_probabilities: dict[str, float]
    posterior_probabilities: dict[str, float]
    tension_score_before: float
    tension_score_after: float
    tension_reduction: float
    reasons: list[str]
    observed_result: ObservedExperimentResult | None = None
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/tension-discovery/v1",
            "run_id": self.run_id,
            "created_at": self.created_at,
            "obligation_id": self.obligation_id,
            "status": self.status,
            "tensions": [item.to_dict() for item in self.tensions],
            "hypotheses": [item.to_dict() for item in self.hypotheses],
            "experiments": [item.to_dict() for item in self.experiments],
            "recommendation": self.recommendation.to_dict() if self.recommendation else None,
            "prior_probabilities": self.prior_probabilities,
            "posterior_probabilities": self.posterior_probabilities,
            "tension_score_before": self.tension_score_before,
            "tension_score_after": self.tension_score_after,
            "tension_reduction": self.tension_reduction,
            "reasons": self.reasons,
            "observed_result": self.observed_result.to_dict() if self.observed_result else None,
        }
