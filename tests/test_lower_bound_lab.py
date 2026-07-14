from __future__ import annotations

import json
from pathlib import Path

from nexus_u.benchmark.lower_bound import run_lower_bound_benchmark
from nexus_u.lower_bounds import LowerBoundDiscoveryLab, load_challenge
from nexus_u.storage.sqlite import ControlStore


def test_builtin_challenge_preserves_open_lower_bound() -> None:
    report = LowerBoundDiscoveryLab().run(load_challenge())
    assert report.integrity_valid
    assert report.summary["proved_upper_bound_present"] is True
    assert report.summary["unconditional_universal_lower_bound_status"] == "OPEN"
    assert report.summary["best_available_lower_bound_route"] == "CONDITIONAL_THEOREM"
    assert report.summary["matrix_transposition_route_conditional"] is True
    assert report.summary["no_false_solution_claim"] is True


def test_promotion_firewall_blocks_scope_and_evidence_inflation() -> None:
    report = LowerBoundDiscoveryLab().run(load_challenge())
    audits = {item.candidate_id: item for item in report.audits}
    for candidate in (
        "empirical_timings_prove_optimality",
        "consensus_proves_optimality",
        "online_transfers_offline",
        "information_counting_only",
        "bounded_circuit_universalized",
    ):
        assert audits[candidate].decision.value == "REJECT_PROMOTION"
    assert audits["transpose_route_is_complete"].decision.value == "HOLD_CONDITIONAL"
    assert audits["record_open_problem_honestly"].decision.value == "ACCEPT"
    assert audits["online_result_as_restricted_progress"].decision.value == "ACCEPT_RESTRICTED"


def test_research_agenda_contains_high_leverage_route() -> None:
    report = LowerBoundDiscoveryLab().run(load_challenge())
    ids = [item.target_id for item in report.agenda]
    assert "transposition_lower_bound" in ids
    assert "formalize_2025_transposition_reduction" in ids
    assert "proof_barrier_catalog" in ids
    assert len(ids) >= 4


def test_benchmark_and_signature_artifacts(tmp_path: Path) -> None:
    report, path = run_lower_bound_benchmark(output_dir=tmp_path, signing_secret="test-secret")
    summary = report.summary()
    assert summary["pass_rate"] == 1.0
    assert summary["lab_false_promotions"] == 0
    assert summary["promotion_safety_advantage"] == 1.0
    assert path.is_file()
    assert (tmp_path / "lower-bound-lab.signed.json").is_file()


def test_lower_bound_run_persists(tmp_path: Path) -> None:
    report = LowerBoundDiscoveryLab().run(load_challenge())
    store = ControlStore(tmp_path / "control.db")
    store.record_lower_bound_run(report)
    loaded = store.get_lower_bound_run(report.run_id)
    assert loaded is not None
    assert loaded["challenge_id"] == report.challenge_id
    assert loaded["universal_status"] == "OPEN"
    assert loaded["payload"]["summary"]["matrix_transposition_route_conditional"] is True
    assert len(store.list_lower_bound_runs(report.challenge_id)) == 1


def test_integrity_rejects_missing_model() -> None:
    raw = load_challenge()
    raw = json.loads(json.dumps(raw))
    raw["problems"][0]["machine_model_id"] = "missing-model"
    report = LowerBoundDiscoveryLab().run(raw)
    assert report.integrity_valid is False
    assert any("missing model" in item for item in report.integrity_errors)


def test_reduction_cycle_is_rejected() -> None:
    raw = json.loads(json.dumps(load_challenge()))
    raw["reductions"].append({
        "reduction_id": "reverse_cycle",
        "source_problem_id": "integer_multiplication_offline",
        "target_problem_id": "binary_matrix_transposition",
        "premise_bound": "Omega(n log n)",
        "consequence_bound": "Omega(m^2 log m)",
        "status": "HEURISTIC",
        "evidence_kind": "NONE",
        "source_ids": ["harvey_vdh_2025"],
        "model_preserving": True,
        "size_map": "unspecified",
        "overhead": "unspecified",
        "assumptions": []
    })
    report = LowerBoundDiscoveryLab().run(raw)
    assert not report.integrity_valid
    assert "Reduction graph contains a dependency cycle" in report.integrity_errors


def test_model_preserving_reduction_requires_same_model() -> None:
    raw = json.loads(json.dumps(load_challenge()))
    raw["reductions"][0]["source_problem_id"] = "integer_multiplication_online"
    report = LowerBoundDiscoveryLab().run(raw)
    assert not report.integrity_valid
    assert any("claims model preservation" in item for item in report.integrity_errors)
