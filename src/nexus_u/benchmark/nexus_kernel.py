from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable

from nexus_u.kernel.ast import App, Const, EMPTY, EmptyElim, Lam, PROP, Pi, Sort, Var
from nexus_u.kernel.codec import term_from_dict, term_to_dict, write_json
from nexus_u.kernel.core import KernelLimits, NexusKernel, TypeCheckError
from nexus_u.kernel.environment import Environment
from nexus_u.kernel.theorems import proof_bundle, sensitivity_to_query_core, verify_bundle
from nexus_u.security.signing import write_signed_envelope


@dataclass(slots=True)
class NexusKernelReport:
    started_at: float
    completed_at: float
    proof_bundle: dict[str, Any]
    checks: dict[str, bool]
    mutations: dict[str, bool]
    trusted_core: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        all_checks = all(self.checks.values())
        all_mutations = all(self.mutations.values())
        return {
            "check_count": len(self.checks) + len(self.mutations),
            "checks_passed": sum(self.checks.values()) + sum(self.mutations.values()),
            "all_checks_passed": all_checks,
            "all_mutations_rejected": all_mutations,
            "kernel_status": "NEXUS_KERNEL_VERIFIED" if all_checks and all_mutations else "BLOCKED",
            "kernel_version": self.proof_bundle["kernel"],
            "axiom_count": len(self.proof_bundle["verification"]["axioms"]),
            "external_lean_compatible": False,
            "universal_offline_lower_bound_status": "OPEN",
        }

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": "https://nexus-u.dev/nexus-kernel-benchmark/v1",
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": self.summary(),
            "proof_bundle": self.proof_bundle,
            "checks": self.checks,
            "mutations": self.mutations,
            "trusted_core": self.trusted_core,
        }
        payload["report_sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        return payload


def _rejected(action: Callable[[], object]) -> bool:
    try:
        action()
    except Exception:
        return True
    return False


def _trusted_core_stats() -> dict[str, Any]:
    kernel_dir = Path(__file__).resolve().parents[1] / "kernel"
    trusted = ["ast.py", "ops.py", "environment.py", "core.py", "codec.py"]
    files: list[dict[str, Any]] = []
    total_lines = 0
    forbidden_found: list[str] = []
    for name in trusted:
        path = kernel_dir / name
        text = path.read_text(encoding="utf-8")
        lines = len(text.splitlines())
        total_lines += lines
        for token in ("eval(", "exec(", "pickle", "marshal"):
            if token in text:
                forbidden_found.append(f"{name}:{token}")
        files.append({"path": name, "lines": lines, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    return {
        "files": files,
        "total_lines": total_lines,
        "forbidden_dynamic_execution": forbidden_found,
        "scope": "dependent Pi, lambda, application, let, sums, empty type, definitional equality",
    }


def run_nexus_kernel_benchmark(
    *, output_dir: str | Path, signing_secret: str | None = None, key_id: str = "nexus-kernel-local"
) -> tuple[NexusKernelReport, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    bundle = proof_bundle()
    theorem, proof = sensitivity_to_query_core()
    kernel = NexusKernel()

    encoded_theorem = term_to_dict(theorem)
    encoded_proof = term_to_dict(proof)
    decoded_theorem = term_from_dict(encoded_theorem)
    decoded_proof = term_from_dict(encoded_proof)

    # Delta and beta checks use a transparent identity definition.
    env = Environment()
    delta_kernel = NexusKernel(env)
    identity_type = Pi(PROP, Pi(Var(0), Var(1)))
    identity_value = Lam(PROP, Lam(Var(0), Var(0)))
    delta_kernel.declare_definition("idProp", identity_type, identity_value)
    beta_delta_term = App(App(Const("idProp"), EMPTY), EMPTY)

    strict_kernel = NexusKernel(limits=KernelLimits(max_nodes=4, max_depth=20, max_reductions=100))

    checks = {
        "closed_proof_verified": kernel.verify(proof, theorem)["valid"] is True,
        "serialized_bundle_replayed": verify_bundle(bundle)["bundle_verified"] is True,
        "serialization_round_trip": decoded_theorem == theorem and decoded_proof == proof,
        "proof_is_axiom_free": bundle["verification"]["axioms"] == [],
        "beta_delta_normalization": delta_kernel.normalize(beta_delta_term) == EMPTY,
        "definitional_equality": delta_kernel.convertible(beta_delta_term, EMPTY),
        "deterministic_kernel_digest": bundle["kernel_sha256"] == NexusKernel.source_digest(),
        "resource_limit_enforced": _rejected(lambda: strict_kernel.verify(proof, theorem)),
    }

    mutations = {
        "reject_unbound_variable": _rejected(lambda: kernel.infer(Var(0))),
        "reject_non_function_application": _rejected(lambda: kernel.infer(App(EMPTY, EMPTY))),
        "reject_forged_short_proof": _rejected(lambda: kernel.check(Lam(PROP, Var(0)), theorem)),
        "reject_wrong_theorem": _rejected(lambda: kernel.check(proof, EMPTY)),
        "reject_false_elimination_without_false": _rejected(lambda: kernel.infer(EmptyElim(Lam(EMPTY, Var(0)), EMPTY))),
        "reject_unknown_constant": _rejected(lambda: kernel.infer(Const("fabricated"))),
        "reject_decoder_unknown_tag": _rejected(lambda: term_from_dict({"tag": "TrustMe"})),
        "reject_kernel_digest_substitution": _rejected(lambda: verify_bundle({**bundle, "kernel_sha256": "0" * 64})),
        "reject_bundle_payload_tampering": _rejected(
            lambda: verify_bundle({**bundle, "theorem_id": "forged-theorem-id"})
        ),
    }

    report = NexusKernelReport(started, time.time(), bundle, checks, mutations, _trusted_core_stats())
    path = write_json(report.to_dict(), output / "nexus-kernel-benchmark.json")
    write_json(bundle, output / "nexus-kernel-proof.json")
    if signing_secret:
        write_signed_envelope(report.to_dict(), output / "nexus-kernel-benchmark.signed.json", secret=signing_secret, key_id=key_id)
    return report, path
