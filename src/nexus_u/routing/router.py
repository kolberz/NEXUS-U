from __future__ import annotations

import hashlib
import json
from math import sqrt
from typing import Any, Protocol

from nexus_u.core.obligation_graph import ObligationGraph, ObligationKind, ObligationNode, Severity, SEVERITY_WEIGHT
from .models import RouteDecision, RoutingOutcome, Strategy, StrategyScore
from .stagnation import StagnationDetector


class RoutingStore(Protocol):
    def routing_stats(self, obligation_signature: str | None = None) -> list[dict[str, Any]]: ...
    def recent_routing_outcomes(self, obligation_signature: str, limit: int = 20) -> list[dict[str, Any]]: ...
    def record_routing_outcome(self, outcome: RoutingOutcome | dict[str, Any]) -> None: ...


_DEFAULT_COST = {
    Strategy.TEST: 2.0,
    Strategy.COUNTEREXAMPLE_SEARCH: 4.0,
    Strategy.STATIC_ANALYSIS: 5.0,
    Strategy.FORMAL_PROOF: 24.0,
    Strategy.SIMULATION: 12.0,
    Strategy.DOCUMENTATION_SEARCH: 6.0,
    Strategy.DECOMPOSE: 8.0,
    Strategy.REPAIR_IMPLEMENTATION: 10.0,
    Strategy.RESOURCE_LOWERING: 9.0,
    Strategy.HUMAN_REVIEW: 30.0,
    Strategy.DEFER: 1.0,
    Strategy.REJECT: 1.0,
}

_PRIOR_SUCCESS = {
    Strategy.TEST: 0.76,
    Strategy.COUNTEREXAMPLE_SEARCH: 0.62,
    Strategy.STATIC_ANALYSIS: 0.68,
    Strategy.FORMAL_PROOF: 0.58,
    Strategy.SIMULATION: 0.60,
    Strategy.DOCUMENTATION_SEARCH: 0.52,
    Strategy.DECOMPOSE: 0.66,
    Strategy.REPAIR_IMPLEMENTATION: 0.70,
    Strategy.RESOURCE_LOWERING: 0.74,
    Strategy.HUMAN_REVIEW: 0.90,
    Strategy.DEFER: 0.35,
    Strategy.REJECT: 0.95,
}

_KIND_STRATEGIES: dict[ObligationKind, tuple[Strategy, ...]] = {
    ObligationKind.TEST: (Strategy.TEST, Strategy.REPAIR_IMPLEMENTATION, Strategy.STATIC_ANALYSIS),
    ObligationKind.PROOF: (Strategy.COUNTEREXAMPLE_SEARCH, Strategy.FORMAL_PROOF, Strategy.DECOMPOSE),
    ObligationKind.CLAIM: (Strategy.COUNTEREXAMPLE_SEARCH, Strategy.TEST, Strategy.FORMAL_PROOF, Strategy.DECOMPOSE),
    ObligationKind.SAFETY: (Strategy.STATIC_ANALYSIS, Strategy.SIMULATION, Strategy.FORMAL_PROOF, Strategy.HUMAN_REVIEW),
    ObligationKind.POLICY: (Strategy.STATIC_ANALYSIS, Strategy.DOCUMENTATION_SEARCH, Strategy.HUMAN_REVIEW),
    ObligationKind.RESOURCE: (Strategy.RESOURCE_LOWERING, Strategy.SIMULATION, Strategy.DECOMPOSE),
    ObligationKind.RISK: (Strategy.SIMULATION, Strategy.STATIC_ANALYSIS, Strategy.HUMAN_REVIEW),
    ObligationKind.PROVENANCE: (Strategy.STATIC_ANALYSIS, Strategy.REPAIR_IMPLEMENTATION),
    ObligationKind.SPECIFICATION: (Strategy.DECOMPOSE, Strategy.DOCUMENTATION_SEARCH, Strategy.HUMAN_REVIEW),
    ObligationKind.REQUIREMENT: (Strategy.TEST, Strategy.REPAIR_IMPLEMENTATION, Strategy.DECOMPOSE),
    ObligationKind.ASSUMPTION: (Strategy.DOCUMENTATION_SEARCH, Strategy.TEST, Strategy.HUMAN_REVIEW),
    ObligationKind.INTENT: (Strategy.DECOMPOSE, Strategy.HUMAN_REVIEW),
    ObligationKind.UNKNOWN: (Strategy.DECOMPOSE, Strategy.DOCUMENTATION_SEARCH, Strategy.HUMAN_REVIEW),
}


class ObligationRouter:
    """Cost-aware hybrid router using explicit rules plus Bayesian outcome history."""

    def __init__(self, store: RoutingStore | None = None, *, prior_strength: float = 4.0) -> None:
        self.store = store
        self.prior_strength = max(1.0, prior_strength)
        self.stagnation_detector = StagnationDetector()

    @staticmethod
    def signature(node: ObligationNode) -> str:
        source_family = node.source.split(".", 1)[0] if node.source else "runtime"
        semantic_tags = sorted(str(item) for item in node.metadata.get("routing_tags", []))
        payload = {
            "kind": str(node.kind),
            "severity": str(node.severity),
            "blocking": node.blocking,
            "source_family": source_family,
            "tags": semantic_tags,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        return f"{node.kind}:{node.severity}:{source_family}:{digest}"

    def _stats(self, signature: str) -> dict[Strategy, dict[str, Any]]:
        if self.store is None:
            return {}
        result: dict[Strategy, dict[str, Any]] = {}
        for item in self.store.routing_stats(signature):
            try:
                strategy = Strategy(str(item["strategy"]))
            except (KeyError, ValueError):
                continue
            result[strategy] = item
        return result

    def _recent(self, signature: str) -> list[dict[str, Any]]:
        if self.store is None:
            return []
        return self.store.recent_routing_outcomes(signature, 20)

    def _candidate_strategies(self, node: ObligationNode) -> list[Strategy]:
        candidates = list(_KIND_STRATEGIES.get(node.kind, _KIND_STRATEGIES[ObligationKind.UNKNOWN]))
        if node.metadata.get("requires_human_authority") and Strategy.HUMAN_REVIEW not in candidates:
            candidates.append(Strategy.HUMAN_REVIEW)
        if node.metadata.get("false_or_invalid"):
            return [Strategy.REJECT]
        return candidates

    def recommend(self, graph: ObligationGraph, node_id: str, *, remaining_budget_seconds: float | None = None) -> RouteDecision:
        node = graph.nodes[node_id]
        signature = self.signature(node)
        historical = self._stats(signature)
        recent = self._recent(signature)
        stagnation = self.stagnation_detector.detect(recent)
        severity = SEVERITY_WEIGHT[node.severity]
        scores: list[StrategyScore] = []

        for strategy in self._candidate_strategies(node):
            stats = historical.get(strategy, {})
            attempts = int(stats.get("attempts", 0))
            successes = int(stats.get("successes", 0))
            prior = _PRIOR_SUCCESS[strategy]
            predicted = (successes + prior * self.prior_strength) / (attempts + self.prior_strength)
            expected_cost = float(stats.get("mean_cost_seconds") or _DEFAULT_COST[strategy])
            mean_debt = float(stats.get("mean_debt_delta") or 0.0)
            expected_debt_reduction = max(0.0, -mean_debt) if attempts else severity * predicted * 0.35
            confidence = min(1.0, attempts / 8.0)
            reasons = [f"Prior/historical success estimate {predicted:.3f}", f"Expected cost {expected_cost:.2f}s"]

            if remaining_budget_seconds is not None and expected_cost > remaining_budget_seconds:
                predicted *= 0.25
                reasons.append("Expected cost exceeds remaining budget")
            if stagnation.detected and strategy.value in stagnation.repeated_strategies:
                predicted *= 0.15
                reasons.append(f"Penalized by stagnation: {stagnation.kind}")
            if strategy == Strategy.HUMAN_REVIEW and node.severity == Severity.CRITICAL:
                predicted = max(predicted, 0.94)
                reasons.append("Critical obligation favors accountable human authority")
            if strategy == Strategy.REJECT and node.metadata.get("false_or_invalid"):
                predicted = 0.99
                reasons.append("Obligation explicitly marked invalid")

            failure_penalty = (1.0 - predicted) * severity * (2.5 if node.blocking else 1.0)
            cost_penalty = expected_cost * 0.08
            utility = predicted * severity * 4.0 + expected_debt_reduction - failure_penalty - cost_penalty
            scores.append(StrategyScore(
                strategy=strategy,
                predicted_success=round(predicted, 6),
                expected_cost_seconds=round(expected_cost, 6),
                expected_debt_reduction=round(expected_debt_reduction, 6),
                utility=round(utility, 6),
                confidence=round(confidence, 6),
                attempts=attempts,
                successes=successes,
                reasons=reasons,
            ))

        scores.sort(key=lambda item: (item.utility, item.predicted_success), reverse=True)
        selected = scores[0].strategy
        escalation_required = False
        escalation_reason: str | None = None

        if stagnation.detected:
            escalation_required = node.severity in {Severity.HIGH, Severity.CRITICAL}
            if Strategy.DECOMPOSE in [item.strategy for item in scores] and not escalation_required:
                selected = Strategy.DECOMPOSE
            elif escalation_required:
                selected = Strategy.HUMAN_REVIEW
                if all(item.strategy != Strategy.HUMAN_REVIEW for item in scores):
                    scores.append(StrategyScore(
                        strategy=Strategy.HUMAN_REVIEW,
                        predicted_success=0.90,
                        expected_cost_seconds=_DEFAULT_COST[Strategy.HUMAN_REVIEW],
                        expected_debt_reduction=severity * 0.5,
                        utility=severity * 2.0,
                        confidence=0.0,
                        attempts=0,
                        successes=0,
                        reasons=["Added by stagnation escalation policy"],
                    ))
                escalation_reason = stagnation.explanation

        best = next(item for item in scores if item.strategy == selected)
        if node.severity == Severity.CRITICAL and best.predicted_success < 0.80:
            escalation_required = True
            escalation_reason = escalation_reason or "No automated strategy meets the critical-obligation confidence threshold"
            selected = Strategy.HUMAN_REVIEW
        if node.metadata.get("requires_human_authority"):
            escalation_required = True
            escalation_reason = "Obligation explicitly requires human authority"
            selected = Strategy.HUMAN_REVIEW

        return RouteDecision(
            obligation_id=node_id,
            obligation_signature=signature,
            selected=selected,
            scores=scores,
            escalation_required=escalation_required,
            escalation_reason=escalation_reason,
            stagnation=stagnation,
        )

    def recommend_unresolved(self, graph: ObligationGraph, *, limit: int = 25) -> list[RouteDecision]:
        nodes = sorted(graph.unresolved(), key=lambda item: (SEVERITY_WEIGHT[item.severity], item.blocking), reverse=True)
        return [self.recommend(graph, node.node_id) for node in nodes[: max(1, limit)]]

    def record(self, outcome: RoutingOutcome) -> None:
        if self.store is None:
            raise RuntimeError("Routing outcome persistence requires a store")
        self.store.record_routing_outcome(outcome)
