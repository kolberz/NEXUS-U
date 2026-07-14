from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
import time
import uuid


class ArtifactType(StrEnum):
    THEOREM = "theorem"
    SOFTWARE = "software"
    MODEL = "model"
    SIMULATION = "simulation"
    POLICY = "policy"
    EXPERIMENT = "experiment"
    ARCHITECTURE = "architecture"
    DOCUMENT = "document"
    CREATIVE_WORK = "creative_work"


class TaskMode(StrEnum):
    FORMAL_PROOF = "FORMAL_PROOF"
    SOFTWARE_ENGINEERING = "SOFTWARE_ENGINEERING"
    SCIENTIFIC_MODELING = "SCIENTIFIC_MODELING"
    EXPERIMENTAL_RESEARCH = "EXPERIMENTAL_RESEARCH"
    CONTROL_SYNTHESIS = "CONTROL_SYNTHESIS"
    SYSTEM_ARCHITECTURE = "SYSTEM_ARCHITECTURE"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    CREATIVE_CONSTRUCTION = "CREATIVE_CONSTRUCTION"
    RESOURCE_CONSTRAINED_DEPLOYMENT = "RESOURCE_CONSTRAINED_DEPLOYMENT"
    POLICY_AND_COMPLIANCE = "POLICY_AND_COMPLIANCE"


class EpistemicStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    SPECULATIVE_HYPOTHESIS = "SPECULATIVE_HYPOTHESIS"
    HEURISTIC_STRATEGY = "HEURISTIC_STRATEGY"
    FORMALIZATION_TARGET = "FORMALIZATION_TARGET"
    EMPIRICAL_SUPPORT = "EMPIRICAL_SUPPORT"
    COMPUTATIONAL_EVIDENCE = "COMPUTATIONAL_EVIDENCE"
    EXECUTION_VERIFIED = "EXECUTION_VERIFIED"
    CONDITIONAL_THEOREM = "CONDITIONAL_THEOREM"
    MATHEMATICALLY_DERIVED = "MATHEMATICALLY_DERIVED"
    KERNEL_VERIFIED = "KERNEL_VERIFIED"
    INDEPENDENTLY_REPRODUCED = "INDEPENDENTLY_REPRODUCED"
    REFUTED = "REFUTED"


class RunStatus(StrEnum):
    INTAKE = "INTAKE"
    INTENT_COMPILED = "INTENT_COMPILED"
    ASSUMPTIONS_EXPOSED = "ASSUMPTIONS_EXPOSED"
    TARGET_FORMALIZED = "TARGET_FORMALIZED"
    CANDIDATES_GENERATED = "CANDIDATES_GENERATED"
    FALSIFICATION = "FALSIFICATION"
    OBSTRUCTION_CLASSIFIED = "OBSTRUCTION_CLASSIFIED"
    STRATEGY_ROUTED = "STRATEGY_ROUTED"
    ARTIFACT_CONSTRUCTED = "ARTIFACT_CONSTRUCTED"
    EXECUTED = "EXECUTED"
    VERIFIED = "VERIFIED"
    POLICY_REVIEWED = "POLICY_REVIEWED"
    SAFETY_REVIEWED = "SAFETY_REVIEWED"
    ADVERSARIAL_REVIEWED = "ADVERSARIAL_REVIEWED"
    CERTIFIED = "CERTIFIED"
    CURATED = "CURATED"
    RELEASED = "RELEASED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    REFUTED = "REFUTED"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class ResourceBudget:
    wall_clock_seconds: float = 30.0
    memory_mb: int = 512
    output_bytes: int = 1_000_000
    external_calls: int = 0


@dataclass(slots=True)
class Evidence:
    kind: str
    summary: str
    uri: str | None = None
    sha256: str | None = None
    verifier: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Claim:
    statement: str
    requested_status: EpistemicStatus = EpistemicStatus.UNKNOWN
    assigned_status: EpistemicStatus = EpistemicStatus.UNKNOWN
    assumptions: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    missing_obligations: list[str] = field(default_factory=list)
    scope: str = ""


@dataclass(slots=True)
class TaskSpec:
    intent: str
    artifact_type: ArtifactType
    modes: list[TaskMode]
    success_conditions: list[str] = field(default_factory=list)
    prohibited_shortcuts: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    adapter: str = "document"
    budget: ResourceBudget = field(default_factory=ResourceBudget)
    initial_obligations: list[dict[str, Any]] = field(default_factory=list)
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(slots=True)
class StageEvent:
    stage: str
    status: str
    message: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ArtifactRecord:
    task: TaskSpec
    status: RunStatus = RunStatus.INTAKE
    artifact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    output: dict[str, Any] = field(default_factory=dict)
    claims: list[Claim] = field(default_factory=list)
    events: list[StageEvent] = field(default_factory=list)
    unresolved_obligations: list[str] = field(default_factory=list)
    policy_decisions: list[dict[str, Any]] = field(default_factory=list)
    audit_root: str | None = None
    evidence_bundle: str | None = None
    obligation_graph_path: str | None = None
    obligation_graph: dict[str, Any] = field(default_factory=dict)
    obligation_summary: dict[str, Any] = field(default_factory=dict)
    obligation_metrics: dict[str, Any] = field(default_factory=dict)
    routing_recommendations: list[dict[str, Any]] = field(default_factory=list)
    epistemic_potential: float = 0.0
    reproducible: bool = False
    released: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
