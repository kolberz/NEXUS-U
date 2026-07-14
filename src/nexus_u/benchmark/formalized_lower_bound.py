from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any

from nexus_u.formalization import FormalizedLowerBoundEngine
from nexus_u.lower_bounds import load_challenge
from nexus_u.security.signing import write_signed_envelope


@dataclass(slots=True)
class FormalizedLowerBoundBenchmarkReport:
    started_at: float
    completed_at: float
    formalization_report: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        source = self.formalization_report["summary"]
        checks = {
            "specialized_certificate_verified": bool(source["specialized_certificate_valid"]),
            "all_adversarial_mutations_rejected": bool(source["all_mutations_rejected"]),
            "proof_assistant_target_generated": bool(source["proof_assistant_target_generated"]),
            "proof_target_contains_no_forbidden_declarations": not source["proof_assistant_target_forbidden_declarations"],
            "external_kernel_not_falsely_claimed": not source["external_kernel_verified"] and not source["kernel_verified_claim_emitted"],
            "restricted_status_is_scoped": source["restricted_theorem_status"] == "SPECIALIZED_CHECKER_VERIFIED",
            "universal_target_remains_open": source["universal_offline_lower_bound_status"] == "OPEN",
            "transposition_plan_is_acyclic": bool(source["transposition_plan_valid"]),
            "transposition_open_premise_preserved": source["transposition_route_status"] == "FORMALIZATION_PLAN_WITH_OPEN_PREMISE",
            "formalization_has_open_obligations": len(source["transposition_open_obligations"]) >= 1,
            "checker_digest_present": len(source["specialized_certificate_digest"]) == 64,
            "no_false_solution_claim": bool(source["no_false_solution_claim"]),
        }
        passed = sum(checks.values())
        return {
            "check_count": len(checks),
            "checks_passed": passed,
            "pass_rate": round(passed / len(checks), 6),
            "specialized_status": source["specialized_certificate_status"],
            "external_kernel_verified": source["external_kernel_verified"],
            "universal_status": source["universal_offline_lower_bound_status"],
            "open_transposition_obligations": len(source["transposition_open_obligations"]),
            "checks": checks,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/formalized-lower-bound-benchmark/v1",
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": self.summary(),
            "formalization_report": self.formalization_report,
        }


def run_formalized_lower_bound_benchmark(
    *,
    output_dir: str | Path,
    signing_secret: str | None = None,
    key_id: str = "formalized-lower-bound-local",
) -> tuple[FormalizedLowerBoundBenchmarkReport, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    report_obj = FormalizedLowerBoundEngine().run(
        load_challenge(), output_dir=output / "formalization"
    )
    report = FormalizedLowerBoundBenchmarkReport(started, time.time(), report_obj.to_dict())
    path = output / "formalized-lower-bound-search.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    if signing_secret:
        write_signed_envelope(
            report.to_dict(),
            output / "formalized-lower-bound-search.signed.json",
            key_id=key_id,
            secret=signing_secret,
        )
    return report, path
