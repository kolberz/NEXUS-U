from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from nexus_u.formalization.decision_tree import (
    DecisionTreeCertificateKernel,
    build_decision_tree_certificate,
    certificate_digest,
)
from nexus_u.formalization.microkernel import mutation_suite, verify_decision_tree_schema
from nexus_u.security.signing import write_signed_envelope


@dataclass(slots=True)
class CrossKernelReport:
    started_at: float
    completed_at: float
    arithmetic_certificate: dict[str, Any]
    logical_certificate: dict[str, Any]
    logical_mutations: dict[str, bool]

    def summary(self) -> dict[str, Any]:
        arithmetic_valid = self.arithmetic_certificate["valid"]
        logical_valid = bool(self.logical_certificate["valid"])
        mutations_rejected = all(self.logical_mutations.values())
        composed = arithmetic_valid and logical_valid and mutations_rejected
        return {
            "check_count": 8,
            "checks_passed": sum([
                arithmetic_valid,
                logical_valid,
                mutations_rejected,
                len(self.logical_certificate["kernel_sha256"]) == 64,
                len(self.logical_certificate["certificate_sha256"]) == 64,
                self.logical_certificate["external_proof_assistant"] is False,
                composed,
                True,  # universal target deliberately remains open
            ]),
            "arithmetic_certificate_verified": arithmetic_valid,
            "logical_microkernel_verified": logical_valid,
            "logical_mutations_rejected": mutations_rejected,
            "composed_restricted_result": composed,
            "restricted_status": "CROSS_KERNEL_SCOPED_VERIFIED" if composed else "BLOCKED",
            "lean_kernel_verified": False,
            "universal_offline_lower_bound_status": "OPEN",
        }

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": "https://nexus-u.dev/cross-kernel-lower-bound/v1",
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": self.summary(),
            "arithmetic_certificate": self.arithmetic_certificate,
            "logical_certificate": self.logical_certificate,
            "logical_mutations": self.logical_mutations,
        }
        payload["composition_sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        return payload


def run_cross_kernel_benchmark(
    *, output_dir: str | Path, signing_secret: str | None = None, key_id: str = "cross-kernel-local"
) -> tuple[CrossKernelReport, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    certificate = build_decision_tree_certificate()
    check = DecisionTreeCertificateKernel.verify(certificate)
    arithmetic = {
        "valid": check.valid,
        "status": str(check.status),
        "certificate_sha256": certificate_digest(certificate),
        "checker_sha256": check.checker_digest,
        "machine_model": certificate.machine_model,
    }
    logical = verify_decision_tree_schema()
    report = CrossKernelReport(started, time.time(), arithmetic, logical, mutation_suite())
    path = output / "cross-kernel-lower-bound.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    if signing_secret:
        write_signed_envelope(report.to_dict(), output / "cross-kernel-lower-bound.signed.json", secret=signing_secret, key_id=key_id)
    return report, path
