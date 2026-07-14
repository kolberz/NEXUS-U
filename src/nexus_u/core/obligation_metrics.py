from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any

from .obligation_graph import ObligationGraph, ObligationKind, ObligationStatus, SEVERITY_WEIGHT, STATUS_FACTOR


@dataclass(slots=True)
class ObligationMetrics:
    created: int = 0
    discharged: int = 0
    refuted: int = 0
    deferred: int = 0
    escalated: int = 0
    transferred: int = 0
    evidence_added: int = 0
    reopened: int = 0
    initial_active: int = 0
    final_active: int = 0
    active_delta: int = 0
    initial_weighted_debt: float = 0.0
    final_weighted_debt: float = 0.0
    weighted_debt_delta: float = 0.0
    weight_resolved: float = 0.0
    resolution_ratio: float = 0.0
    mean_discharge_seconds: float | None = None
    maximum_discharge_seconds: float | None = None
    critical_created: int = 0
    critical_unresolved: int = 0
    by_operation: dict[str, int] = field(default_factory=dict)
    by_kind: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _node_debt(graph: ObligationGraph, node_id: str) -> float:
    node = graph.nodes[node_id]
    if node.kind == ObligationKind.EVIDENCE:
        return 0.0
    return SEVERITY_WEIGHT[node.severity] * STATUS_FACTOR[node.status]


def compute_obligation_metrics(graph: ObligationGraph) -> ObligationMetrics:
    metrics = ObligationMetrics()
    if graph.events:
        metrics.initial_active = len(graph.events[0].active_before)
        metrics.final_active = len(graph.events[-1].active_after)
    else:
        metrics.initial_active = 0
        metrics.final_active = len(graph.unresolved())
    metrics.active_delta = metrics.final_active - metrics.initial_active

    for event in graph.events:
        metrics.by_operation[event.operation] = metrics.by_operation.get(event.operation, 0) + 1
        if event.operation == "CREATE_OBLIGATION":
            metrics.created += 1
        elif event.operation == "ADD_EVIDENCE":
            metrics.evidence_added += 1
        elif event.operation == "DISCHARGE_OBLIGATION":
            metrics.discharged += 1
        elif event.operation == "REFUTE_OBLIGATION":
            metrics.refuted += 1
        elif event.operation == "DEFER_OBLIGATION":
            metrics.deferred += 1
        elif event.operation == "ESCALATE_OBLIGATION":
            metrics.escalated += 1
        elif event.operation == "TRANSFER_OBLIGATION":
            metrics.transferred += 1
        elif event.operation == "REOPEN_OBLIGATION":
            metrics.reopened += 1

    discharge_durations: list[float] = []
    for node in graph.nodes.values():
        metrics.by_kind[str(node.kind)] = metrics.by_kind.get(str(node.kind), 0) + 1
        if node.severity.value == "CRITICAL" and node.kind != ObligationKind.EVIDENCE:
            metrics.critical_created += 1
            if node.status in {ObligationStatus.OPEN, ObligationStatus.DEFERRED, ObligationStatus.ESCALATED}:
                metrics.critical_unresolved += 1
        if node.status in {ObligationStatus.DISCHARGED, ObligationStatus.REFUTED} and node.kind != ObligationKind.EVIDENCE:
            discharge_durations.append(max(0.0, node.updated_at - node.created_at))

    if discharge_durations:
        metrics.mean_discharge_seconds = round(mean(discharge_durations), 6)
        metrics.maximum_discharge_seconds = round(max(discharge_durations), 6)

    # Gross created weight is the total potential burden introduced during the run.
    # Final debt applies status factors to the same immutable nodes. This makes the
    # resolved amount measurable even though nodes are never deleted.
    metrics.initial_weighted_debt = round(
        sum(SEVERITY_WEIGHT[node.severity] for node in graph.nodes.values() if node.kind != ObligationKind.EVIDENCE),
        6,
    )
    metrics.final_weighted_debt = graph.epistemic_potential()
    metrics.weighted_debt_delta = round(metrics.final_weighted_debt - metrics.initial_weighted_debt, 6)
    metrics.weight_resolved = round(metrics.initial_weighted_debt - metrics.final_weighted_debt, 6)
    metrics.resolution_ratio = round(metrics.weight_resolved / metrics.initial_weighted_debt, 6) if metrics.initial_weighted_debt else 1.0
    return metrics
