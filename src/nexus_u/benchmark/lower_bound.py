from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from typing import Any

from nexus_u.lower_bounds import LowerBoundDiscoveryLab, load_challenge
from nexus_u.security.signing import write_signed_envelope


@dataclass(slots=True)
class LowerBoundBenchmarkReport:
    started_at: float
    completed_at: float
    lab_report: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        source = self.lab_report["summary"]
        audits = self.lab_report["audits"]
        expected_rejections = {
            "empirical_timings_prove_optimality",
            "consensus_proves_optimality",
            "online_transfers_offline",
            "information_counting_only",
            "bounded_circuit_universalized",
        }
        rejected = {item["candidate_id"] for item in audits if item["decision"] == "REJECT_PROMOTION"}
        conditional = {item["candidate_id"] for item in audits if item["decision"] == "HOLD_CONDITIONAL"}
        accepted = {item["candidate_id"] for item in audits if item["decision"] in {"ACCEPT", "ACCEPT_RESTRICTED"}}
        baseline_false_promotions = len(expected_rejections) + (1 if "transpose_route_is_complete" in conditional else 0)
        lab_false_promotions = len(expected_rejections - rejected)
        checks = {
            "integrity_valid": bool(source["integrity_valid"]),
            "proved_upper_bound_present": bool(source["proved_upper_bound_present"]),
            "unconditional_lower_bound_remains_open": source["unconditional_universal_lower_bound_status"] == "OPEN",
            "conditional_transposition_route_preserved": bool(source["matrix_transposition_route_conditional"]),
            "all_invalid_promotions_blocked": expected_rejections.issubset(rejected),
            "reduction_overclaim_held_conditional": "transpose_route_is_complete" in conditional,
            "honest_open_and_restricted_progress_accepted": {"record_open_problem_honestly", "online_result_as_restricted_progress"}.issubset(accepted),
            "research_agenda_nonempty": source["open_high_leverage_targets"] >= 4,
            "no_false_solution_claim": bool(source["no_false_solution_claim"]),
        }
        passed = sum(checks.values())
        return {
            "check_count": len(checks),
            "checks_passed": passed,
            "pass_rate": round(passed / len(checks), 6),
            "baseline_false_promotions": baseline_false_promotions,
            "lab_false_promotions": lab_false_promotions,
            "promotion_safety_advantage": round((baseline_false_promotions - lab_false_promotions) / max(1, baseline_false_promotions), 6),
            "checks": checks,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/lower-bound-lab-benchmark/v1",
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": self.summary(),
            "lab_report": self.lab_report,
        }


def run_lower_bound_benchmark(
    challenge: str | Path | dict[str, Any] | None = None,
    *,
    output_dir: str | Path,
    signing_secret: str | None = None,
    key_id: str = "lower-bound-lab-local",
) -> tuple[LowerBoundBenchmarkReport, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    lab_report = LowerBoundDiscoveryLab().run(load_challenge(challenge)).to_dict()
    report = LowerBoundBenchmarkReport(started, time.time(), lab_report)
    path = output / "lower-bound-lab.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    if signing_secret:
        write_signed_envelope(report.to_dict(), output / "lower-bound-lab.signed.json", key_id=key_id, secret=signing_secret)
    return report, path
