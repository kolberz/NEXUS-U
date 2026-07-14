from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import tempfile
import time
from typing import Any

from nexus_u.core.obligation_graph import ObligationGraph, ObligationKind, Severity
from nexus_u.routing import ObligationRouter, RoutingOutcome, Strategy
from nexus_u.security.signing import write_signed_envelope
from nexus_u.storage.sqlite import ControlStore


@dataclass(slots=True)
class RoutingBenchmarkCase:
    case_id: str
    expected: Strategy
    selected: Strategy
    static_baseline: Strategy
    matched: bool
    baseline_matched: bool
    escalation_required: bool
    predicted_success: float
    expected_cost_seconds: float
    stagnation_kind: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RoutingBenchmarkReport:
    started_at: float
    completed_at: float
    cases: list[RoutingBenchmarkCase]

    def summary(self) -> dict[str, Any]:
        total = len(self.cases)
        matches = sum(item.matched for item in self.cases)
        baseline_matches = sum(item.baseline_matched for item in self.cases)
        return {
            "case_count": total,
            "router_matches": matches,
            "router_match_rate": round(matches / total, 6) if total else 0.0,
            "static_baseline_matches": baseline_matches,
            "static_baseline_match_rate": round(baseline_matches / total, 6) if total else 0.0,
            "routing_advantage": round((matches - baseline_matches) / total, 6) if total else 0.0,
            "escalations": sum(item.escalation_required for item in self.cases),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/obligation-router-benchmark/v1",
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": self.summary(),
            "cases": [item.to_dict() for item in self.cases],
        }


def _graph(statement: str, kind: ObligationKind, severity: Severity, **metadata: Any) -> tuple[ObligationGraph, str]:
    graph = ObligationGraph("routing-benchmark")
    node_id = graph.add_node(statement, kind=kind, severity=severity, metadata=metadata)
    return graph, node_id


def _seed(store: ControlStore, router: ObligationRouter, graph: ObligationGraph, node_id: str, entries: list[tuple[Strategy, bool, float, float]]) -> None:
    signature = router.signature(graph.nodes[node_id])
    base = time.time() - len(entries)
    for index, (strategy, success, cost, debt_delta) in enumerate(entries):
        outcome = RoutingOutcome(
            obligation_signature=signature,
            strategy=strategy,
            success=success,
            cost_seconds=cost,
            debt_delta=debt_delta,
            result="synthetic benchmark history",
            obligation_id=node_id,
            created_at=base + index,
        )
        store.record_routing_outcome(outcome)


def run_routing_benchmark(
    *,
    output_dir: str | Path,
    signing_secret: str | None = None,
    key_id: str = "obligation-router-local",
) -> tuple[RoutingBenchmarkReport, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    cases: list[RoutingBenchmarkCase] = []

    with tempfile.TemporaryDirectory(prefix="nexus-router-benchmark-") as temp:
        store = ControlStore(Path(temp) / "routing.db")
        router = ObligationRouter(store)
        definitions: list[tuple[str, ObligationGraph, str, Strategy, list[tuple[Strategy, bool, float, float]]]] = []

        graph, node = _graph("Release behavior must be regression tested", ObligationKind.TEST, Severity.HIGH)
        definitions.append(("learned_test", graph, node, Strategy.TEST, [
            (Strategy.TEST, True, 1.0, -5.0), (Strategy.TEST, True, 1.2, -4.0),
            (Strategy.TEST, True, 0.9, -6.0), (Strategy.REPAIR_IMPLEMENTATION, False, 8.0, 1.0),
        ]))

        graph, node = _graph("Prove the invariant from approved axioms", ObligationKind.PROOF, Severity.HIGH)
        definitions.append(("formal_proof", graph, node, Strategy.FORMAL_PROOF, [
            (Strategy.FORMAL_PROOF, True, 12.0, -8.0), (Strategy.FORMAL_PROOF, True, 15.0, -7.0),
            (Strategy.COUNTEREXAMPLE_SEARCH, False, 3.0, 0.0),
        ]))

        graph, node = _graph("Fit execution within the memory budget", ObligationKind.RESOURCE, Severity.HIGH)
        definitions.append(("resource_lowering", graph, node, Strategy.RESOURCE_LOWERING, [
            (Strategy.RESOURCE_LOWERING, True, 4.0, -6.0), (Strategy.RESOURCE_LOWERING, True, 5.0, -5.0),
            (Strategy.SIMULATION, False, 10.0, 0.0),
        ]))

        graph, node = _graph("Resolve repeated implementation failure", ObligationKind.REQUIREMENT, Severity.HIGH)
        definitions.append(("stagnation_escalation", graph, node, Strategy.HUMAN_REVIEW, [
            (Strategy.TEST, False, 2.0, 0.0), (Strategy.REPAIR_IMPLEMENTATION, False, 7.0, 1.0),
            (Strategy.TEST, False, 2.0, 0.0), (Strategy.REPAIR_IMPLEMENTATION, False, 8.0, 0.0),
        ]))

        graph, node = _graph(
            "Approve a constitutional policy exception",
            ObligationKind.POLICY,
            Severity.CRITICAL,
            requires_human_authority=True,
        )
        definitions.append(("human_authority", graph, node, Strategy.HUMAN_REVIEW, []))

        graph, node = _graph(
            "Reject a known-invalid premise",
            ObligationKind.CLAIM,
            Severity.HIGH,
            false_or_invalid=True,
        )
        definitions.append(("reject_invalid", graph, node, Strategy.REJECT, []))

        for case_id, graph, node_id, expected, history in definitions:
            _seed(store, router, graph, node_id, history)
            decision = router.recommend(graph, node_id)
            selected_score = next((score for score in decision.scores if score.strategy == decision.selected), decision.scores[0])
            baseline = Strategy.TEST
            cases.append(RoutingBenchmarkCase(
                case_id=case_id,
                expected=expected,
                selected=decision.selected,
                static_baseline=baseline,
                matched=decision.selected == expected,
                baseline_matched=baseline == expected,
                escalation_required=decision.escalation_required,
                predicted_success=selected_score.predicted_success,
                expected_cost_seconds=selected_score.expected_cost_seconds,
                stagnation_kind=decision.stagnation.kind,
            ))

    report = RoutingBenchmarkReport(started, time.time(), cases)
    path = output / "routing-benchmark.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    if signing_secret:
        write_signed_envelope(report.to_dict(), output / "routing-benchmark.signed.json", key_id=key_id, secret=signing_secret)
    return report, path
