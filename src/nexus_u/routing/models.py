from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
import time
import uuid


class Strategy(StrEnum):
    TEST = "TEST"
    COUNTEREXAMPLE_SEARCH = "COUNTEREXAMPLE_SEARCH"
    STATIC_ANALYSIS = "STATIC_ANALYSIS"
    FORMAL_PROOF = "FORMAL_PROOF"
    SIMULATION = "SIMULATION"
    DOCUMENTATION_SEARCH = "DOCUMENTATION_SEARCH"
    DECOMPOSE = "DECOMPOSE"
    REPAIR_IMPLEMENTATION = "REPAIR_IMPLEMENTATION"
    RESOURCE_LOWERING = "RESOURCE_LOWERING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    DEFER = "DEFER"
    REJECT = "REJECT"


@dataclass(slots=True)
class StrategyScore:
    strategy: Strategy
    predicted_success: float
    expected_cost_seconds: float
    expected_debt_reduction: float
    utility: float
    confidence: float
    attempts: int
    successes: int
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StagnationReport:
    detected: bool = False
    kind: str | None = None
    failed_attempts: int = 0
    repeated_strategies: list[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RouteDecision:
    obligation_id: str
    obligation_signature: str
    selected: Strategy
    scores: list[StrategyScore]
    escalation_required: bool = False
    escalation_reason: str | None = None
    stagnation: StagnationReport = field(default_factory=StagnationReport)
    policy_version: str = "obligation-router-v1"
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RoutingOutcome:
    obligation_signature: str
    strategy: Strategy
    success: bool
    cost_seconds: float
    debt_delta: float = 0.0
    artifact_id: str | None = None
    obligation_id: str | None = None
    result: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    outcome_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
