from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus_u.benchmark.nexus_kernel import run_nexus_kernel_benchmark
from nexus_u.kernel.ast import App, Const, EMPTY, EmptyElim, Lam, PROP, Pi, Sort, SumType, Var
from nexus_u.kernel.codec import term_from_dict, term_to_dict
from nexus_u.kernel.core import KernelLimits, NexusKernel, TypeCheckError
from nexus_u.kernel.environment import Environment
from nexus_u.kernel.ops import substitute_top
from nexus_u.kernel.theorems import proof_bundle, sensitivity_to_query_core, verify_bundle


def test_constructive_theorem_is_checked_without_axioms() -> None:
    theorem, proof = sensitivity_to_query_core()
    result = NexusKernel().verify(proof, theorem)
    assert result["valid"] is True
    assert result["axioms"] == []


def test_serialized_proof_replays() -> None:
    bundle = proof_bundle()
    assert verify_bundle(bundle)["bundle_verified"] is True
    assert term_from_dict(bundle["theorem"]) == sensitivity_to_query_core()[0]


def test_beta_and_delta_reduction() -> None:
    kernel = NexusKernel(Environment())
    identity_type = Pi(PROP, Pi(Var(0), Var(1)))
    identity = Lam(PROP, Lam(Var(0), Var(0)))
    kernel.declare_definition("idProp", identity_type, identity)
    expression = App(App(Const("idProp"), EMPTY), EMPTY)
    assert kernel.normalize(expression) == EMPTY
    assert kernel.convertible(expression, EMPTY)


def test_sum_and_empty_rules_reject_forgery() -> None:
    kernel = NexusKernel()
    with pytest.raises(TypeCheckError):
        kernel.infer(App(EMPTY, EMPTY))
    with pytest.raises(TypeCheckError):
        kernel.infer(EmptyElim(Lam(EMPTY, Var(0)), EMPTY))


def test_unbound_variable_and_unknown_constant_are_rejected() -> None:
    kernel = NexusKernel()
    with pytest.raises(TypeCheckError):
        kernel.infer(Var(0))
    with pytest.raises(KeyError):
        kernel.infer(Const("unknown"))


def test_definition_cannot_be_added_with_wrong_type() -> None:
    kernel = NexusKernel()
    with pytest.raises(TypeCheckError):
        kernel.declare_definition("bad", EMPTY, Lam(EMPTY, Var(0)))


def test_decoder_rejects_unknown_tags() -> None:
    with pytest.raises(ValueError):
        term_from_dict({"tag": "TrustMe"})


def test_resource_limit_blocks_oversized_proof() -> None:
    theorem, proof = sensitivity_to_query_core()
    kernel = NexusKernel(limits=KernelLimits(max_nodes=4))
    with pytest.raises(Exception):
        kernel.verify(proof, theorem)


def test_benchmark_rejects_all_mutations(tmp_path: Path) -> None:
    report, path = run_nexus_kernel_benchmark(output_dir=tmp_path, signing_secret="test")
    summary = report.summary()
    assert summary["kernel_status"] == "NEXUS_KERNEL_VERIFIED"
    assert summary["all_mutations_rejected"] is True
    assert summary["axiom_count"] == 0
    assert path.exists()
    data = json.loads(path.read_text())
    assert len(data["report_sha256"]) == 64


def test_kernel_digest_is_stable_within_process() -> None:
    assert NexusKernel.source_digest() == NexusKernel.source_digest()


def test_bundle_digest_detects_payload_tampering() -> None:
    bundle = proof_bundle()
    bundle["theorem_id"] = "forged"
    with pytest.raises(Exception):
        verify_bundle(bundle)
