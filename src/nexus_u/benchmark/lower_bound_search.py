from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any

from nexus_u.lower_bounds import ActiveLowerBoundSearchEngine, load_challenge
from nexus_u.security.signing import write_signed_envelope


@dataclass(slots=True)
class ActiveSearchBenchmarkReport:
    started_at: float
    completed_at: float
    search_report: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        report = self.search_report
        source = report["summary"]
        attacks = {item["route_id"]: item for item in report["attacks"]}
        rankings = report["rankings"]
        invalid = {
            "landauer_erasure_optimality",
            "empirical_crossover_extrapolation",
            "online_bound_transfer",
            "bounded_circuit_transfer",
        }
        blocked = {route_id for route_id, attack in attacks.items() if attack["status"] == "BLOCKED"}
        nexus_top3 = [item["route_id"] for item in rankings[:3]]
        candidates = {item["route_id"]: item for item in report["candidates"]}
        naive_top3 = [
            item[0] for item in sorted(
                ((route_id, candidate["novelty"]) for route_id, candidate in candidates.items()),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        ]
        naive_invalid = sum(item in invalid for item in naive_top3)
        nexus_invalid = sum(item in invalid for item in nexus_top3)
        checks = {
            "candidate_portfolio_nontrivial": source["candidate_count"] >= 9,
            "all_known_invalid_routes_blocked": invalid.issubset(blocked),
            "restricted_query_certificate_valid": bool(source["restricted_query_certificate_valid"]),
            "restricted_result_present": source["derived_restricted_count"] >= 1,
            "formalization_route_present": source["formalization_ready_count"] >= 1,
            "universal_target_remains_open": source["universal_offline_lower_bound_status"] == "OPEN",
            "no_false_solution_claim": bool(source["no_false_solution_claim"]),
            "nexus_top_routes_clean": nexus_invalid == 0,
            "naive_novelty_baseline_selects_invalid_route": naive_invalid >= 1,
            "obligation_reduction_positive": source["total_expected_obligation_reduction"] > 0,
        }
        passed = sum(checks.values())
        return {
            "check_count": len(checks),
            "checks_passed": passed,
            "pass_rate": round(passed / len(checks), 6),
            "naive_top3": naive_top3,
            "nexus_top3": nexus_top3,
            "naive_invalid_top3": naive_invalid,
            "nexus_invalid_top3": nexus_invalid,
            "search_safety_advantage": round((naive_invalid - nexus_invalid) / max(1, naive_invalid), 6),
            "checks": checks,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/active-lower-bound-search-benchmark/v1",
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": self.summary(),
            "search_report": self.search_report,
        }


def run_active_lower_bound_search_benchmark(
    *,
    output_dir: str | Path,
    signing_secret: str | None = None,
    key_id: str = "active-lower-bound-search-local",
    max_certificate_n: int = 16,
) -> tuple[ActiveSearchBenchmarkReport, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    search = ActiveLowerBoundSearchEngine().run(load_challenge(), max_certificate_n=max_certificate_n).to_dict()
    report = ActiveSearchBenchmarkReport(started, time.time(), search)
    path = output / "active-lower-bound-search.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    if signing_secret:
        write_signed_envelope(
            report.to_dict(),
            output / "active-lower-bound-search.signed.json",
            key_id=key_id,
            secret=signing_secret,
        )
    return report, path
