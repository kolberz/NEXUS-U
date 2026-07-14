from __future__ import annotations

import hashlib
import json
from typing import Any

from .ast import Term
from .codec import term_from_dict, term_to_dict
from .core import KernelError, NexusKernel
from .surface import SApp, SCase, SEmpty, SEmptyElim, SLam, SPi, SSort, SSum, SVar, elaborate


def _arrow(left: Any, right: Any) -> SPi:
    return SPi("_", left, right)


def sensitivity_to_query_surface() -> tuple[Any, Any]:
    prop = SSort(0)
    empty = SEmpty()
    q = SVar("queried")
    same = SVar("same")
    equal = SVar("equal")
    not_q = _arrow(q, empty)
    not_equal = _arrow(equal, empty)
    preserve = _arrow(not_q, same)
    exact = _arrow(same, equal)
    decidable = SSum(q, not_q)

    theorem = SPi(
        "queried", prop,
        SPi(
            "same", prop,
            SPi(
                "equal", prop,
                SPi(
                    "not_equal", not_equal,
                    SPi(
                        "preserve", preserve,
                        SPi(
                            "path_exact", exact,
                            SPi("decide", decidable, q),
                        ),
                    ),
                ),
            ),
        ),
    )

    contradiction = SApp(
        SVar("not_equal"),
        SApp(SVar("path_exact"), SApp(SVar("preserve"), SVar("not_queried"))),
    )
    proof = SLam(
        "queried", prop,
        SLam(
            "same", prop,
            SLam(
                "equal", prop,
                SLam(
                    "not_equal", not_equal,
                    SLam(
                        "preserve", preserve,
                        SLam(
                            "path_exact", exact,
                            SLam(
                                "decide", decidable,
                                SCase(
                                    SVar("decide"),
                                    SLam("queried_proof", q, SVar("queried_proof")),
                                    SLam("not_queried", not_q, SEmptyElim(contradiction, q)),
                                    q,
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    return theorem, proof


def sensitivity_to_query_core() -> tuple[Term, Term]:
    theorem, proof = sensitivity_to_query_surface()
    return elaborate(theorem), elaborate(proof)


def proof_bundle() -> dict[str, Any]:
    theorem, proof = sensitivity_to_query_core()
    kernel = NexusKernel()
    verification = kernel.verify(proof, theorem)
    payload: dict[str, Any] = {
        "schema": "https://nexus-u.dev/nexus-kernel-proof/v1",
        "kernel": kernel.version,
        "kernel_sha256": kernel.source_digest(),
        "theorem_id": "sensitivity-to-query-constructive-v1",
        "scope": "generic deterministic decision-path sensitivity lemma with explicit decidability",
        "theorem": term_to_dict(theorem),
        "proof": term_to_dict(proof),
        "verification": verification,
        "external_lean_compatible": False,
        "universal_integer_multiplication_lower_bound": "OPEN",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["bundle_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def verify_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    if bundle.get("schema") != "https://nexus-u.dev/nexus-kernel-proof/v1":
        raise KernelError("unsupported proof-bundle schema")
    expected_bundle_hash = bundle.get("bundle_sha256")
    unsigned = {key: value for key, value in bundle.items() if key != "bundle_sha256"}
    actual_bundle_hash = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if not expected_bundle_hash or expected_bundle_hash != actual_bundle_hash:
        raise KernelError("proof bundle digest mismatch")
    theorem = term_from_dict(bundle["theorem"])
    proof = term_from_dict(bundle["proof"])
    kernel = NexusKernel()
    result = kernel.verify(proof, theorem)
    expected_kernel = bundle.get("kernel_sha256")
    if expected_kernel and expected_kernel != result["kernel_sha256"]:
        raise KernelError("proof bundle targets a different kernel digest")
    result["theorem_id"] = bundle.get("theorem_id")
    result["bundle_verified"] = True
    return result
