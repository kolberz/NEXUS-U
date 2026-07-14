from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
import time
import uuid

from .models import ClaimStatus, EvidenceKind, ObstructionKind


class ProofRouteKind(StrEnum):
    FORMALIZE_REDUCTION = "FORMALIZE_REDUCTION"
    RESTRICTED_THEOREM = "RESTRICTED_THEOREM"
    DATA_MOVEMENT = "DATA_MOVEMENT"
    COMMUNICATION_CUT = "COMMUNICATION_CUT"
    MODEL_TRANSFER = "MODEL_TRANSFER"
    INFORMATION_COUNTING = "INFORMATION_COUNTING"
    EMPIRICAL_EXTRAPOLATION = "EMPIRICAL_EXTRAPOLATION"
    BARRIER_THEOREM = "BARRIER_THEOREM"


class RouteStatus(StrEnum):
    PROPOSED = "PROPOSED"
    CONDITIONAL = "CONDITIONAL"
    FORMALIZATION_READY = "FORMALIZATION_READY"
    DERIVED_RESTRICTED = "DERIVED_RESTRICTED"
    BLOCKED = "BLOCKED"
    REFUTED = "REFUTED"


class AttackKind(StrEnum):
    MODEL_SCOPE = "MODEL_SCOPE"
    EMPIRICAL_ONLY = "EMPIRICAL_ONLY"
    OPEN_PREMISE = "OPEN_PREMISE"
    REVERSIBILITY = "REVERSIBILITY"
    INFORMATION_COST_GAP = "INFORMATION_COST_GAP"
    UNIVERSALIZATION = "UNIVERSALIZATION"
    REDUCTION_OVERHEAD = "REDUCTION_OVERHEAD"
    TAUTOLOGY = "TAUTOLOGY"
    MISSING_MECHANISM = "MISSING_MECHANISM"
    MISSING_FALSIFICATION = "MISSING_FALSIFICATION"
    NONE = "NONE"


@dataclass(slots=True)
class ProofRouteCandidate:
    route_id: str
    title: str
    kind: ProofRouteKind
    target_problem_id: str
    target_model_id: str
    statement: str
    target_complexity: str
    requested_status: ClaimStatus
    evidence_kind: EvidenceKind
    mechanism: str
    assumptions: list[str] = field(default_factory=list)
    proof_obligations: list[str] = field(default_factory=list)
    falsification_tests: list[str] = field(default_factory=list)
    leverage: float = 0.5
    novelty: float = 0.5
    tractability: float = 0.5
    estimated_cost: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RouteAttack:
    route_id: str
    attacks: list[AttackKind]
    inherited_obstructions: list[ObstructionKind]
    reasons: list[str]
    survives: bool
    status: RouteStatus
    obligation_debt: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RestrictedLemmaCertificate:
    certificate_id: str
    theorem: str
    machine_model: str
    bound: str
    witness: str
    proof_steps: list[str]
    verified_instances: list[dict[str, Any]]
    status: RouteStatus
    kernel_verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RankedRoute:
    route_id: str
    title: str
    status: RouteStatus
    score: float
    expected_obligation_reduction: float
    obligation_debt: float
    rationale: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ActiveSearchReport:
    challenge_id: str
    candidates: list[ProofRouteCandidate]
    attacks: list[RouteAttack]
    rankings: list[RankedRoute]
    certificates: list[RestrictedLemmaCertificate]
    summary: dict[str, Any]
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/active-lower-bound-search/v1",
            "run_id": self.run_id,
            "created_at": self.created_at,
            "challenge_id": self.challenge_id,
            "candidates": [item.to_dict() for item in self.candidates],
            "attacks": [item.to_dict() for item in self.attacks],
            "rankings": [item.to_dict() for item in self.rankings],
            "certificates": [item.to_dict() for item in self.certificates],
            "summary": self.summary,
        }
