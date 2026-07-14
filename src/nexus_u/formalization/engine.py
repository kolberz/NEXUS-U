from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .decision_tree import (
    DecisionTreeCertificateKernel,
    build_decision_tree_certificate,
    certificate_digest,
    write_lean_target,
)
from .models import FormalizedLowerBoundReport
from .plan import build_transposition_formalization_plan, verify_plan


class FormalizedLowerBoundEngine:
    def run(self, challenge: dict[str, Any], *, output_dir: str | Path) -> FormalizedLowerBoundReport:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        certificate = build_decision_tree_certificate()
        check = DecisionTreeCertificateKernel.verify(certificate)
        check.mutation_resistance = DecisionTreeCertificateKernel.mutation_suite(certificate)
        lean_path = write_lean_target(output / "DecisionTreeMultiplicationTarget.lean")
        lean_text = lean_path.read_text(encoding="utf-8")
        plan = build_transposition_formalization_plan()
        plan_valid, plan_errors, plan_order = verify_plan(plan)
        external_kernel_available = False
        forbidden = [token for token in ("sorry", "admit", "axiom") if f"\n{token} " in lean_text.lower()]
        theorem_target = {
            "format": "Lean 4 source target",
            "path": str(lean_path),
            "sha256": hashlib.sha256(lean_text.encode("utf-8")).hexdigest(),
            "contains_forbidden_declarations": forbidden,
            "external_kernel_available": external_kernel_available,
            "external_kernel_verified": False,
            "status": "PROOF_ASSISTANT_READY",
        }
        open_plan = [item.obligation_id for item in plan if item.status.value != "DISCHARGED"]
        summary = {
            "specialized_certificate_valid": check.valid,
            "specialized_certificate_status": check.status.value,
            "specialized_certificate_digest": certificate_digest(certificate),
            "mutation_checks": check.mutation_resistance,
            "all_mutations_rejected": all(check.mutation_resistance.values()),
            "proof_assistant_target_generated": lean_path.is_file(),
            "proof_assistant_target_forbidden_declarations": forbidden,
            "external_kernel_available": external_kernel_available,
            "external_kernel_verified": False,
            "kernel_verified_claim_emitted": False,
            "restricted_theorem_status": check.status.value,
            "universal_offline_lower_bound_status": "OPEN",
            "transposition_route_status": "FORMALIZATION_PLAN_WITH_OPEN_PREMISE",
            "transposition_plan_valid": plan_valid,
            "transposition_plan_errors": plan_errors,
            "transposition_plan_order": plan_order,
            "transposition_open_obligations": open_plan,
            "no_false_solution_claim": check.valid and not external_kernel_available,
            "formalization_status": "SPECIALIZED_CERTIFICATE_VERIFIED_EXTERNAL_KERNEL_PENDING",
        }
        return FormalizedLowerBoundReport(
            challenge_id=str(challenge.get("challenge_id", "integer-multiplication-optimality")),
            certificate=certificate,
            certificate_check=check,
            theorem_target=theorem_target,
            transposition_plan=plan,
            summary=summary,
        )
