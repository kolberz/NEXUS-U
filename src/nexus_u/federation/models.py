from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import time
from typing import Any
import uuid


class ActorRole(StrEnum):
    CONTRIBUTOR = "CONTRIBUTOR"
    REVIEWER = "REVIEWER"
    VERIFIER = "VERIFIER"
    SECURITY = "SECURITY"
    COMPLIANCE = "COMPLIANCE"
    RELEASE_MANAGER = "RELEASE_MANAGER"
    OWNER = "OWNER"


class EvidenceVerdict(StrEnum):
    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    INCONCLUSIVE = "INCONCLUSIVE"


class FederationDecisionStatus(StrEnum):
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    CONFLICT = "CONFLICT"
    INSUFFICIENT_QUORUM = "INSUFFICIENT_QUORUM"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"


@dataclass(slots=True)
class FederationActor:
    actor_id: str
    organization_id: str
    roles: list[ActorRole]
    key_id: str
    trust_weight: float = 1.0
    authority_scopes: list[str] = field(default_factory=lambda: ["*"])
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EvidenceSubmission:
    obligation_id: str
    actor_id: str
    organization_id: str
    verdict: EvidenceVerdict
    evidence_kind: str
    summary: str
    evidence_digest: str
    provenance_group: str
    scope: str = "global"
    repository: str | None = None
    commit: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    submission_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    signature: str | None = None
    key_id: str | None = None

    def signing_payload(self) -> dict[str, Any]:
        raw = asdict(self)
        raw.pop("signature", None)
        return raw

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class QuorumPolicy:
    policy_id: str
    minimum_organizations: int = 2
    minimum_weight: float = 2.0
    minimum_independent_evidence: int = 2
    required_roles: list[ActorRole] = field(default_factory=list)
    veto_roles: list[ActorRole] = field(default_factory=lambda: [ActorRole.SECURITY])
    allow_inconclusive: bool = True
    require_no_conflicts: bool = True
    required_dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FederationDecision:
    obligation_id: str
    policy_id: str
    status: FederationDecisionStatus
    reasons: list[str]
    supporting_submissions: list[str] = field(default_factory=list)
    refuting_submissions: list[str] = field(default_factory=list)
    inconclusive_submissions: list[str] = field(default_factory=list)
    participating_organizations: list[str] = field(default_factory=list)
    independent_evidence_groups: list[str] = field(default_factory=list)
    total_weight: float = 0.0
    missing_roles: list[str] = field(default_factory=list)
    missing_dependencies: list[str] = field(default_factory=list)
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    @property
    def approved(self) -> bool:
        return self.status == FederationDecisionStatus.APPROVED

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["approved"] = self.approved
        return raw
