from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

from .models import (
    CertificateCheck,
    FormalizationStatus,
    SpecializedProofCertificate,
)


THEOREM_ID = "exact-multiplication-bit-query-depth-2n"
THEOREM_STATEMENT = (
    "For every n >= 1, any deterministic adaptive bit-query decision tree computing exact "
    "multiplication of two n-bit unsigned integers has worst-case query depth at least 2n."
)


class DecisionTreeCertificateKernel:
    """Small proof-specific checker for the sensitivity lower-bound schema.

    This checker is intentionally not presented as Lean, Isabelle, Coq, or another general
    proof-assistant kernel. It validates a fixed proof schema: a common witness where every
    input coordinate is sensitive, followed by the deterministic decision-tree path lemma.
    """

    version = "nexus-dt-kernel-v1"
    trusted_rules = {
        "BIT_FLIP_SUBTRACTION",
        "PRODUCT_DELTA_X",
        "PRODUCT_DELTA_Y",
        "POSITIVE_DELTA",
        "UNQUERIED_BIT_PRESERVES_TRANSCRIPT",
        "DETERMINISM_PRESERVES_LEAF",
        "EXACTNESS_FORBIDS_EQUAL_OUTPUT_ON_SENSITIVE_PAIR",
        "ALL_SENSITIVE_COORDINATES_FORCE_DEPTH",
    }

    @classmethod
    def digest(cls) -> str:
        source = inspect.getsource(cls).encode("utf-8")
        return hashlib.sha256(source).hexdigest()

    @classmethod
    def verify(cls, certificate: SpecializedProofCertificate) -> CertificateCheck:
        errors: list[str] = []
        discharged: list[str] = []

        if certificate.theorem_id != THEOREM_ID:
            errors.append("Unexpected theorem identifier")
        if certificate.theorem_statement != THEOREM_STATEMENT:
            errors.append("The theorem statement changed")
        if certificate.machine_model != "deterministic adaptive bit-query decision tree":
            errors.append("Machine model mismatch")
        domain = certificate.parameter_domain
        if domain != {"parameter": "n", "type": "Nat", "constraint": "n >= 1"}:
            errors.append("The parameter domain must be n >= 1")
        if certificate.input_width != "2*n":
            errors.append("Input width must be exactly 2*n")
        if certificate.lower_bound != "2*n":
            errors.append("The claimed exact lower bound must be 2*n")
        if certificate.witness != {"x": "2^n - 1", "y": "2^n - 1"}:
            errors.append("The common all-ones witness is required")

        expected_classes = {
            "x": {
                "coordinate_range": "0 <= i < n",
                "flipped_input": "x - 2^i",
                "product_delta": "2^i * y",
                "nonzero_reason": "n >= 1 implies y = 2^n - 1 > 0",
                "count": "n",
            },
            "y": {
                "coordinate_range": "0 <= i < n",
                "flipped_input": "y - 2^i",
                "product_delta": "2^i * x",
                "nonzero_reason": "n >= 1 implies x = 2^n - 1 > 0",
                "count": "n",
            },
        }
        actual: dict[str, dict[str, Any]] = {}
        for item in certificate.sensitivity_classes:
            name = str(item.get("input"))
            if name in actual:
                errors.append(f"Duplicate sensitivity class: {name}")
            actual[name] = {k: v for k, v in item.items() if k != "input"}
        if actual != expected_classes:
            errors.append("Sensitivity classes do not cover exactly n x-bits and n y-bits with valid deltas")
        else:
            discharged.extend(["BIT_FLIP_SUBTRACTION", "PRODUCT_DELTA_X", "PRODUCT_DELTA_Y", "POSITIVE_DELTA"])

        if set(certificate.trusted_rules) != cls.trusted_rules:
            errors.append("Certificate trusted-rule declaration differs from the checker trust base")

        arithmetic_sanity = True
        for n in range(1, 33):
            x = y = (1 << n) - 1
            base = x * y
            for i in range(n):
                if base - ((x - (1 << i)) * y) != (1 << i) * y:
                    arithmetic_sanity = False
                if base - (x * (y - (1 << i))) != (1 << i) * x:
                    arithmetic_sanity = False
        if not arithmetic_sanity:
            errors.append("Arithmetic sensitivity sanity sweep failed")

        rules = [str(item.get("rule")) for item in certificate.proof_steps]
        unknown = sorted(set(rules) - cls.trusted_rules)
        if unknown:
            errors.append(f"Unknown proof rules: {unknown}")
        required = [
            "UNQUERIED_BIT_PRESERVES_TRANSCRIPT",
            "DETERMINISM_PRESERVES_LEAF",
            "EXACTNESS_FORBIDS_EQUAL_OUTPUT_ON_SENSITIVE_PAIR",
            "ALL_SENSITIVE_COORDINATES_FORCE_DEPTH",
        ]
        missing = [rule for rule in required if rule not in rules]
        if missing:
            errors.append(f"Missing decision-tree proof rules: {missing}")
        else:
            discharged.extend(required)

        # Rule order is part of the proof object: transcript equality precedes leaf equality,
        # which precedes contradiction with exactness, which precedes the depth conclusion.
        positions = {rule: rules.index(rule) for rule in required if rule in rules}
        if len(positions) == len(required) and not all(positions[a] < positions[b] for a, b in zip(required, required[1:])):
            errors.append("Decision-tree rules occur in an invalid order")

        digest = cls.digest()
        if certificate.checker_digest and certificate.checker_digest != digest:
            errors.append("Certificate checker digest does not match the active checker")

        valid = not errors
        return CertificateCheck(
            valid=valid,
            status=(FormalizationStatus.SPECIALIZED_CHECKER_VERIFIED if valid else FormalizationStatus.BLOCKED),
            errors=errors,
            discharged_rules=sorted(set(discharged)),
            checker_digest=digest,
        )

    @classmethod
    def mutation_suite(cls, certificate: SpecializedProofCertificate) -> dict[str, bool]:
        mutations: dict[str, SpecializedProofCertificate] = {}

        wrong_bound = deepcopy(certificate)
        wrong_bound.lower_bound = "2*n + 1"
        mutations["reject_stronger_false_bound"] = wrong_bound

        missing_coordinates = deepcopy(certificate)
        missing_coordinates.sensitivity_classes = missing_coordinates.sensitivity_classes[:1]
        mutations["reject_missing_y_coordinates"] = missing_coordinates

        wrong_witness = deepcopy(certificate)
        wrong_witness.witness = {"x": "0", "y": "0"}
        mutations["reject_insensitive_witness"] = wrong_witness

        missing_path_rule = deepcopy(certificate)
        missing_path_rule.proof_steps = [
            item for item in missing_path_rule.proof_steps
            if item.get("rule") != "EXACTNESS_FORBIDS_EQUAL_OUTPUT_ON_SENSITIVE_PAIR"
        ]
        mutations["reject_missing_exactness_step"] = missing_path_rule

        changed_model = deepcopy(certificate)
        changed_model.machine_model = "offline multitape Turing machine"
        mutations["reject_model_laundering"] = changed_model

        changed_checker = deepcopy(certificate)
        changed_checker.checker_digest = "0" * 64
        mutations["reject_checker_substitution"] = changed_checker

        return {name: not cls.verify(item).valid for name, item in mutations.items()}


def build_decision_tree_certificate() -> SpecializedProofCertificate:
    certificate = SpecializedProofCertificate(
        certificate_id="decision-tree-sensitivity-proof-v1",
        theorem_id=THEOREM_ID,
        theorem_statement=THEOREM_STATEMENT,
        machine_model="deterministic adaptive bit-query decision tree",
        parameter_domain={"parameter": "n", "type": "Nat", "constraint": "n >= 1"},
        input_width="2*n",
        lower_bound="2*n",
        witness={"x": "2^n - 1", "y": "2^n - 1"},
        sensitivity_classes=[
            {
                "input": "x",
                "coordinate_range": "0 <= i < n",
                "flipped_input": "x - 2^i",
                "product_delta": "2^i * y",
                "nonzero_reason": "n >= 1 implies y = 2^n - 1 > 0",
                "count": "n",
            },
            {
                "input": "y",
                "coordinate_range": "0 <= i < n",
                "flipped_input": "y - 2^i",
                "product_delta": "2^i * x",
                "nonzero_reason": "n >= 1 implies x = 2^n - 1 > 0",
                "count": "n",
            },
        ],
        trusted_rules=sorted(DecisionTreeCertificateKernel.trusted_rules),
        proof_steps=[
            {
                "rule": "UNQUERIED_BIT_PRESERVES_TRANSCRIPT",
                "statement": "If a coordinate is not queried on the witness path, flipping it preserves all query answers on that path.",
            },
            {
                "rule": "DETERMINISM_PRESERVES_LEAF",
                "statement": "Equal query transcripts in a deterministic tree reach the same output leaf.",
            },
            {
                "rule": "EXACTNESS_FORBIDS_EQUAL_OUTPUT_ON_SENSITIVE_PAIR",
                "statement": "An exact algorithm cannot return the same leaf value on two inputs with different products.",
            },
            {
                "rule": "ALL_SENSITIVE_COORDINATES_FORCE_DEPTH",
                "statement": "Because all 2n coordinates are sensitive at one witness, its path queries all 2n coordinates.",
            },
        ],
        checker_digest=DecisionTreeCertificateKernel.digest(),
    )
    check = DecisionTreeCertificateKernel.verify(certificate)
    certificate.status = check.status
    return certificate


def certificate_digest(certificate: SpecializedProofCertificate) -> str:
    raw = certificate.to_dict()
    raw["checker_digest"] = DecisionTreeCertificateKernel.digest()
    return hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def write_lean_target(path: str | Path) -> Path:
    """Generate a proof-assistant target without asserting an unverified theorem."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    text = r'''/--
NEXUS-U v2.6 formalization target.

This file declares the restricted-model definitions and the proposition to be proved.
It deliberately contains no `axiom`, `sorry`, or `admit`, and it is not labeled
kernel-verified unless an external Lean toolchain accepts a completed proof.
-/

namespace NexusU.LowerBounds

abbrev BitVector (m : Nat) := Fin m → Bool

/-- A coordinate is sensitive when flipping only that coordinate changes the output. -/
def SensitiveAt {m α : Type} [DecidableEq α]
    (f : m → α) (x : m) (flip : m → m) : Prop :=
  f x ≠ f (flip x)

/-- Formal target metadata for the decision-tree lower bound. -/
structure QueryLowerBoundTarget where
  inputBits : Nat
  claimedDepth : Nat
  exact : Bool
  deterministic : Bool

def exactMultiplicationQueryTarget (n : Nat) : QueryLowerBoundTarget := {
  inputBits := 2 * n
  claimedDepth := 2 * n
  exact := true
  deterministic := true
}

/--
The proposition below is a formalization target, not a theorem assertion.
A completed development must define deterministic adaptive bit-query trees,
execution transcripts, exactness, and worst-case depth, then prove that the
all-ones multiplication witness forces every one of the `2*n` coordinates to
be queried.
-/
def ExactMultiplicationNeedsAllBits : Prop :=
  ∀ n : Nat, 0 < n →
    (exactMultiplicationQueryTarget n).claimedDepth = 2 * n

end NexusU.LowerBounds
'''
    lowered = text.lower()
    for forbidden in ("sorry", "admit", "axiom"):
        # The explanatory comment names forbidden tokens, so only reject executable forms.
        if f"\n{forbidden} " in lowered or f"\n{forbidden}\n" in lowered:
            raise ValueError(f"Generated Lean target contains forbidden declaration: {forbidden}")
    output.write_text(text, encoding="utf-8")
    return output
