from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any

from nexus_u.formalization.kernel_bridge import KernelBridgeEngine, PINNED_LEAN_TOOLCHAIN, PINNED_LEAN_VERSION
from nexus_u.formalization.kernel_receipts import (
    KernelReceiptFederation,
    KernelRunnerIdentity,
    ReceiptSignatureProfile,
    build_receipt_request,
    make_reference_receipt,
)
from nexus_u.security.signing import write_signed_envelope


@dataclass(slots=True)
class KernelReceiptBenchmark:
    started_at: float
    completed_at: float
    request: dict[str, Any]
    decision: dict[str, Any]
    checks: dict[str, bool]

    def summary(self) -> dict[str, Any]:
        passed = sum(self.checks.values())
        return {
            "check_count": len(self.checks),
            "checks_passed": passed,
            "pass_rate": passed / len(self.checks),
            "quorum_status": self.decision["status"],
            "theorem_status": self.decision["theorem_status"],
            "external_independence_claimed": self.decision["external_independence_claimed"],
            "universal_target_status": self.decision["universal_target_status"],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/kernel-receipt-benchmark/v1",
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": self.summary(),
            "request": self.request,
            "decision": self.decision,
            "checks": self.checks,
        }


def run_kernel_receipt_benchmark(*, output_dir: str | Path, signing_secret: str | None = None, key_id: str = "kernel-receipt-local") -> tuple[KernelReceiptBenchmark, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    project = KernelBridgeEngine.write_project(output / "kernel-receipt-project")
    request = build_receipt_request(project_dir=project, theorem="allSensitive_forces_allQueried", toolchain=PINNED_LEAN_TOOLCHAIN, version_fragment=PINNED_LEAN_VERSION)
    (output / "kernel-receipt-request.json").write_text(json.dumps(request.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    federation = KernelReceiptFederation(request)
    runners = [
        KernelRunnerIdentity("runner-a", "org-a", "infra-a", "key-a", platform_family="linux"),
        KernelRunnerIdentity("runner-b", "org-b", "infra-b", "key-b", platform_family="macos"),
    ]
    for runner, secret in zip(runners, ("secret-a", "secret-b"), strict=True):
        federation.register_runner(runner, secret=secret)
        federation.submit(make_reference_receipt(request, runner, salt=runner.runner_id))
    decision = federation.evaluate()

    checks = {
        "request_hashes_present": len(request.project_sha256) == 64 and len(request.source_sha256) == 64,
        "two_organizations_counted": len(decision.organizations) == 2,
        "two_provenance_groups_counted": len(decision.provenance_groups) == 2,
        "platform_diversity_recorded": len(decision.platform_families) == 2,
        "local_process_quorum_only": str(decision.status) == "LOCAL_PROCESS_QUORUM",
        "external_independence_not_claimed": decision.external_independence_claimed is False,
        "kernel_promotion_withheld": decision.theorem_status == "KERNEL_RECEIPT_QUORUM_PENDING_EXTERNAL",
        "universal_target_open": decision.universal_target_status == "OPEN",
    }
    report = KernelReceiptBenchmark(time.time(), time.time(), request.to_dict(), decision.to_dict(), checks)
    path = output / "kernel-receipt-federation.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    if signing_secret:
        write_signed_envelope(report.to_dict(), output / "kernel-receipt-federation.signed.json", secret=signing_secret, key_id=key_id)
    return report, path
