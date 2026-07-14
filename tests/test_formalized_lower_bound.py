from __future__ import annotations

from copy import deepcopy

from nexus_u.formalization import (
    DecisionTreeCertificateKernel,
    FormalizedLowerBoundEngine,
    build_decision_tree_certificate,
    build_transposition_formalization_plan,
    verify_plan,
)
from nexus_u.lower_bounds import load_challenge


def test_specialized_certificate_verifies_and_mutations_fail(tmp_path):
    certificate = build_decision_tree_certificate()
    result = DecisionTreeCertificateKernel.verify(certificate)
    assert result.valid
    mutations = DecisionTreeCertificateKernel.mutation_suite(certificate)
    assert mutations
    assert all(mutations.values())


def test_checker_rejects_trust_base_mutation():
    certificate = build_decision_tree_certificate()
    certificate.trusted_rules = certificate.trusted_rules[:-1]
    result = DecisionTreeCertificateKernel.verify(certificate)
    assert not result.valid
    assert any("trust base" in item for item in result.errors)


def test_transposition_plan_is_acyclic_and_preserves_open_premise():
    plan = build_transposition_formalization_plan()
    valid, errors, order = verify_plan(plan)
    assert valid, errors
    assert order[0] == "T0"
    assert order[-1] == "T8"
    assert any(item.status.value != "DISCHARGED" for item in plan)


def test_transposition_plan_rejects_cycle():
    plan = build_transposition_formalization_plan()
    broken = deepcopy(plan)
    broken[0].dependencies = ["T8"]
    valid, errors, _ = verify_plan(broken)
    assert not valid
    assert any("cycle" in item for item in errors)


def test_engine_keeps_external_kernel_and_universal_target_open(tmp_path):
    report = FormalizedLowerBoundEngine().run(load_challenge(), output_dir=tmp_path)
    summary = report.summary
    assert summary["specialized_certificate_valid"]
    assert summary["all_mutations_rejected"]
    assert summary["proof_assistant_target_generated"]
    assert not summary["external_kernel_verified"]
    assert not summary["kernel_verified_claim_emitted"]
    assert summary["universal_offline_lower_bound_status"] == "OPEN"
    assert summary["transposition_plan_valid"]
    assert summary["transposition_open_obligations"]
