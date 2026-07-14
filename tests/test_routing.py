from __future__ import annotations

from pathlib import Path
import tempfile

from nexus_u.benchmark.routing import run_routing_benchmark
from nexus_u.core.obligation_graph import ObligationGraph, ObligationKind, Severity
from nexus_u.routing import ObligationRouter, RoutingOutcome, Strategy
from nexus_u.storage.sqlite import ControlStore


def _node(kind=ObligationKind.REQUIREMENT, severity=Severity.HIGH, **metadata):
    graph = ObligationGraph("test-routing")
    node_id = graph.add_node("Resolve this obligation", kind=kind, severity=severity, metadata=metadata)
    return graph, node_id


def test_router_learns_success_and_cost():
    with tempfile.TemporaryDirectory() as tmp:
        store = ControlStore(Path(tmp) / "routing.db")
        graph, node_id = _node(ObligationKind.TEST)
        router = ObligationRouter(store)
        signature = router.signature(graph.nodes[node_id])
        for cost in (0.8, 1.0, 1.2):
            store.record_routing_outcome(RoutingOutcome(signature, Strategy.TEST, True, cost, -4.0))
        for cost in (7.0, 9.0):
            store.record_routing_outcome(RoutingOutcome(signature, Strategy.REPAIR_IMPLEMENTATION, False, cost, 1.0))
        decision = router.recommend(graph, node_id)
        assert decision.selected == Strategy.TEST
        assert decision.scores[0].attempts >= 3


def test_router_detects_oscillation_and_escalates():
    with tempfile.TemporaryDirectory() as tmp:
        store = ControlStore(Path(tmp) / "routing.db")
        graph, node_id = _node(ObligationKind.REQUIREMENT, Severity.HIGH)
        router = ObligationRouter(store)
        signature = router.signature(graph.nodes[node_id])
        for strategy in (Strategy.TEST, Strategy.REPAIR_IMPLEMENTATION, Strategy.TEST, Strategy.REPAIR_IMPLEMENTATION):
            store.record_routing_outcome(RoutingOutcome(signature, strategy, False, 2.0, 0.0))
        decision = router.recommend(graph, node_id)
        assert decision.stagnation.detected
        assert decision.stagnation.kind == "OSCILLATION"
        assert decision.escalation_required
        assert decision.selected == Strategy.HUMAN_REVIEW


def test_router_requires_human_authority():
    graph, node_id = _node(ObligationKind.POLICY, Severity.CRITICAL, requires_human_authority=True)
    decision = ObligationRouter().recommend(graph, node_id)
    assert decision.selected == Strategy.HUMAN_REVIEW
    assert decision.escalation_required


def test_routing_benchmark_beats_static_baseline(tmp_path: Path):
    report, path = run_routing_benchmark(output_dir=tmp_path, signing_secret="test-secret")
    assert path.exists()
    assert (tmp_path / "routing-benchmark.signed.json").exists()
    summary = report.summary()
    assert summary["router_match_rate"] == 1.0
    assert summary["routing_advantage"] > 0.5
