from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any

from nexus_u.formalization.kernel_bridge import KernelBridgeEngine, KernelBridgeReport
from nexus_u.security.signing import write_signed_envelope


@dataclass(slots=True)
class KernelBridgeBenchmarkReport:
    started_at: float
    completed_at: float
    bridge_report: KernelBridgeReport

    def summary(self) -> dict[str, Any]:
        report = self.bridge_report
        execution = report.execution
        checks = {
            "proof_project_generated": Path(report.project_path).is_dir(),
            "static_checks_pass": bool(report.static_checks.get("passed")),
            "generic_sensitivity_theorem_present": bool(report.static_checks.get("theorem_present")),
            "multiplication_specialization_present": bool(report.static_checks.get("multiplication_specialization_present")),
            "no_forbidden_declarations": not report.static_checks.get("forbidden_declarations"),
            "pinned_toolchain": bool(report.static_checks.get("pinned_toolchain_present")),
            "replay_manifest_present": Path(report.replay_manifest_path).is_file(),
            "ci_kernel_job_present": bool(report.static_checks.get("ci_workflow_present")),
            "no_false_kernel_claim": execution.verified or report.status == "PROOF_PROJECT_READY_KERNEL_PENDING",
            "universal_target_remains_open": report.universal_target_status == "OPEN",
            "toolchain_unavailability_is_explicit": execution.available or execution.status == "EXTERNAL_KERNEL_PENDING",
            "kernel_status_consistent": (report.status == "KERNEL_VERIFIED") == execution.verified,
        }
        passed = sum(bool(value) for value in checks.values())
        return {
            "check_count": len(checks),
            "checks_passed": passed,
            "pass_rate": round(passed / len(checks), 6),
            "bridge_status": report.status,
            "external_kernel_available": execution.available,
            "external_kernel_verified": execution.verified,
            "trusted_toolchain_identity": execution.trusted_identity,
            "universal_status": report.universal_target_status,
            "checks": checks,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/kernel-bridge-benchmark/v1",
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": self.summary(),
            "bridge_report": self.bridge_report.to_dict(),
        }


def run_kernel_bridge_benchmark(
    *,
    output_dir: str | Path,
    signing_secret: str | None = None,
    key_id: str = "kernel-bridge-local",
    explicit_lean: str | None = None,
    explicit_lake: str | None = None,
) -> tuple[KernelBridgeBenchmarkReport, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    bridge = KernelBridgeEngine(explicit_lean=explicit_lean, explicit_lake=explicit_lake).run(
        output / "kernel-bridge"
    )
    report = KernelBridgeBenchmarkReport(started, time.time(), bridge)
    path = output / "kernel-verification-bridge.json"
    import json
    path.write_text(json.dumps(report.to_dict(), indent=2, default=str), encoding="utf-8")
    if signing_secret:
        write_signed_envelope(
            report.to_dict(),
            output / "kernel-verification-bridge.signed.json",
            secret=signing_secret,
            key_id=key_id,
        )
    return report, path
