from pathlib import Path

from nexus_u.benchmark.microkernel import run_cross_kernel_benchmark
from nexus_u.formalization.microkernel import (
    NaturalDeductionMicrokernel,
    decision_tree_schema,
    mutation_suite,
    verify_decision_tree_schema,
)


def test_microkernel_checks_decision_tree_schema() -> None:
    theorem, proof, decidable = decision_tree_schema()
    assert NaturalDeductionMicrokernel.infer(proof, decidable=decidable) == theorem
    report = verify_decision_tree_schema()
    assert report["valid"] is True
    assert len(report["kernel_sha256"]) == 64


def test_microkernel_rejects_mutations() -> None:
    mutations = mutation_suite()
    assert len(mutations) >= 5
    assert all(mutations.values())


def test_cross_kernel_benchmark(tmp_path: Path) -> None:
    report, path = run_cross_kernel_benchmark(output_dir=tmp_path)
    summary = report.summary()
    assert summary["composed_restricted_result"] is True
    assert summary["restricted_status"] == "CROSS_KERNEL_SCOPED_VERIFIED"
    assert summary["lean_kernel_verified"] is False
    assert summary["universal_offline_lower_bound_status"] == "OPEN"
    assert path.is_file()
