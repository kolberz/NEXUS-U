from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CandidateScore:
    candidate_id: str
    score: float
    feasible: bool
    metrics: dict[str, float]
    violations: tuple[str, ...]
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    winner: CandidateScore | None
    ranking: tuple[CandidateScore, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "winner": asdict(self.winner) if self.winner else None,
            "ranking": [asdict(item) for item in self.ranking],
        }


def evaluate_candidates(
    candidates: list[dict[str, Any]],
    *,
    weights: dict[str, float],
    constraints: dict[str, dict[str, float]] | None = None,
) -> DiscoveryResult:
    constraints = constraints or {}
    ranking: list[CandidateScore] = []
    for index, candidate in enumerate(candidates):
        candidate_id = str(candidate.get("id", f"candidate-{index + 1}"))
        raw_metrics = candidate.get("metrics", {})
        if not isinstance(raw_metrics, dict):
            raise ValueError(f"{candidate_id}.metrics must be an object")
        metrics = {str(key): float(value) for key, value in raw_metrics.items()}
        violations: list[str] = []
        for metric, rule in constraints.items():
            if metric not in metrics:
                violations.append(f"missing metric {metric}")
                continue
            if "min" in rule and metrics[metric] < float(rule["min"]):
                violations.append(f"{metric} below minimum")
            if "max" in rule and metrics[metric] > float(rule["max"]):
                violations.append(f"{metric} above maximum")
        score = sum(metrics.get(metric, 0.0) * float(weight) for metric, weight in weights.items())
        ranking.append(
            CandidateScore(
                candidate_id=candidate_id,
                score=score,
                feasible=not violations,
                metrics=metrics,
                violations=tuple(violations),
                payload=dict(candidate.get("payload", {})),
            )
        )
    ranking.sort(key=lambda item: (item.feasible, item.score), reverse=True)
    winner = next((item for item in ranking if item.feasible), None)
    return DiscoveryResult(winner=winner, ranking=tuple(ranking))
