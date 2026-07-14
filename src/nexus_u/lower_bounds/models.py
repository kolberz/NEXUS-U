from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
import time
import uuid


class BoundKind(StrEnum):
    UPPER = "UPPER"
    LOWER = "LOWER"


class ClaimStatus(StrEnum):
    PROVED = "PROVED"
    PUBLISHED_RESULT = "PUBLISHED_RESULT"
    CONDITIONAL_THEOREM = "CONDITIONAL_THEOREM"
    OPEN = "OPEN"
    EMPIRICAL = "EMPIRICAL"
    HEURISTIC = "HEURISTIC"
    REFUTED = "REFUTED"
    UNKNOWN = "UNKNOWN"
    FORMALIZATION_TARGET = "FORMALIZATION_TARGET"


class EvidenceKind(StrEnum):
    PEER_REVIEWED_PROOF = "PEER_REVIEWED_PROOF"
    PUBLISHED_PROOF = "PUBLISHED_PROOF"
    FORMAL_PROOF = "FORMAL_PROOF"
    PROVED_REDUCTION = "PROVED_REDUCTION"
    EMPIRICAL_TIMING = "EMPIRICAL_TIMING"
    FINITE_TESTS = "FINITE_TESTS"
    INFORMATION_COUNTING = "INFORMATION_COUNTING"
    CONSENSUS = "CONSENSUS"
    NONE = "NONE"


class AuditDecision(StrEnum):
    ACCEPT = "ACCEPT"
    ACCEPT_RESTRICTED = "ACCEPT_RESTRICTED"
    HOLD_CONDITIONAL = "HOLD_CONDITIONAL"
    REJECT_PROMOTION = "REJECT_PROMOTION"


class ObstructionKind(StrEnum):
    MODEL_MISMATCH = "MODEL_MISMATCH"
    ONLINE_OFFLINE_GAP = "ONLINE_OFFLINE_GAP"
    RESTRICTED_TO_UNIVERSAL_GAP = "RESTRICTED_TO_UNIVERSAL_GAP"
    INFORMATION_COUNTING_TOO_WEAK = "INFORMATION_COUNTING_TOO_WEAK"
    REVERSIBILITY_ESCAPE = "REVERSIBILITY_ESCAPE"
    REDUCTION_PREMISE_OPEN = "REDUCTION_PREMISE_OPEN"
    REDUCTION_OVERHEAD = "REDUCTION_OVERHEAD"
    EMPIRICAL_TO_ASYMPTOTIC_GAP = "EMPIRICAL_TO_ASYMPTOTIC_GAP"
    CIRCUIT_TO_TURING_TRANSFER_GAP = "CIRCUIT_TO_TURING_TRANSFER_GAP"
    UNPROVED_TRANSPOSE_BOUND = "UNPROVED_TRANSPOSE_BOUND"
    MISSING_SOURCE = "MISSING_SOURCE"
    NONE = "NONE"


@dataclass(slots=True)
class SourceRecord:
    source_id: str
    title: str
    authors: list[str]
    year: int
    source_type: str
    url: str
    doi: str | None = None
    primary: bool = True
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MachineModel:
    model_id: str
    name: str
    input_encoding: str
    access_pattern: str
    online: bool = False
    randomized: bool = False
    tape_count: str | int | None = None
    bounded_coefficients: bool | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProblemDefinition:
    problem_id: str
    name: str
    machine_model_id: str
    size_parameter: str
    input_description: str
    output_description: str
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BoundClaim:
    claim_id: str
    problem_id: str
    kind: BoundKind
    complexity: str
    status: ClaimStatus
    evidence_kind: EvidenceKind
    source_ids: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    scope: str = ""
    statement: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReductionRecord:
    reduction_id: str
    source_problem_id: str
    target_problem_id: str
    premise_bound: str
    consequence_bound: str
    status: ClaimStatus
    evidence_kind: EvidenceKind
    source_ids: list[str]
    model_preserving: bool
    size_map: str
    overhead: str
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CandidateClaim:
    candidate_id: str
    statement: str
    target_problem_id: str
    requested_status: ClaimStatus
    evidence_kind: EvidenceKind
    source_problem_id: str | None = None
    source_model_id: str | None = None
    target_model_id: str | None = None
    assumptions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CandidateAudit:
    candidate_id: str
    decision: AuditDecision
    allowed_status: ClaimStatus
    obstructions: list[ObstructionKind]
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TheoremTarget:
    target_id: str
    statement: str
    problem_id: str
    target_status: ClaimStatus
    prerequisites: list[str]
    leverage: float
    difficulty: float
    scope: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ResearchAgendaItem:
    target_id: str
    statement: str
    priority: float
    rationale: list[str]
    prerequisites: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LowerBoundLabReport:
    challenge_id: str
    integrity_valid: bool
    integrity_errors: list[str]
    claims: list[BoundClaim]
    reductions: list[ReductionRecord]
    audits: list[CandidateAudit]
    agenda: list[ResearchAgendaItem]
    summary: dict[str, Any]
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/lower-bound-lab/v1",
            "run_id": self.run_id,
            "created_at": self.created_at,
            "challenge_id": self.challenge_id,
            "integrity_valid": self.integrity_valid,
            "integrity_errors": self.integrity_errors,
            "claims": [item.to_dict() for item in self.claims],
            "reductions": [item.to_dict() for item in self.reductions],
            "audits": [item.to_dict() for item in self.audits],
            "agenda": [item.to_dict() for item in self.agenda],
            "summary": self.summary,
        }
