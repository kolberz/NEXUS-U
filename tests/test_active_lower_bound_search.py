from __future__ import annotations

from pathlib import Path

from nexus_u.benchmark.lower_bound_search import run_active_lower_bound_search_benchmark
from nexus_u.lower_bounds import ActiveLowerBoundSearchEngine, load_challenge


def test_active_search_preserves_open_universal_target() -> None:
    report = ActiveLowerBoundSearchEngine().run(load_challenge())
    assert report.summary["universal_offline_lower_bound_status"] == "OPEN"
    assert report.summary["no_false_solution_claim"] is True
    assert report.summary["active_search_status"] == "RESTRICTED_PROGRESS_WITH_OPEN_UNIVERSAL_TARGET"


def test_restricted_query_certificate_is_valid_and_scoped() -> None:
    report = ActiveLowerBoundSearchEngine().run(load_challenge(), max_certificate_n=12)
    certificate = report.certificates[0]
    assert certificate.status.value == "DERIVED_RESTRICTED"
    assert certificate.kernel_verified is False
    assert len(certificate.verified_instances) == 12
    assert all(item["valid"] for item in certificate.verified_instances)
    assert all(item["sensitive_bits"] == 2 * item["n"] for item in certificate.verified_instances)
    assert "decision tree" in certificate.machine_model


def test_invalid_routes_are_blocked_before_ranking() -> None:
    report = ActiveLowerBoundSearchEngine().run(load_challenge())
    attacks = {item.route_id: item for item in report.attacks}
    for route_id in (
        "landauer_erasure_optimality",
        "empirical_crossover_extrapolation",
        "online_bound_transfer",
        "bounded_circuit_transfer",
    ):
        assert attacks[route_id].status.value == "BLOCKED"
        assert attacks[route_id].survives is False
    assert all(item.status.value != "BLOCKED" for item in report.rankings[:3])


def test_search_ranks_real_obligation_reduction() -> None:
    report = ActiveLowerBoundSearchEngine().run(load_challenge())
    assert report.rankings
    assert report.rankings[0].score > 0
    assert report.rankings[0].expected_obligation_reduction > 0
    ids = {item.route_id for item in report.rankings[:4]}
    assert "query_model_read_all_bits" in ids
    assert "formalize_transposition_reduction" in ids


def test_active_search_benchmark_and_signature(tmp_path: Path) -> None:
    report, path = run_active_lower_bound_search_benchmark(
        output_dir=tmp_path,
        signing_secret="test-secret",
    )
    summary = report.summary()
    assert summary["pass_rate"] == 1.0
    assert summary["nexus_invalid_top3"] == 0
    assert summary["naive_invalid_top3"] >= 1
    assert summary["search_safety_advantage"] == 1.0
    assert path.is_file()
    assert (tmp_path / "active-lower-bound-search.signed.json").is_file()


def test_active_search_persists(tmp_path: Path) -> None:
    from nexus_u.storage.sqlite import ControlStore

    report = ActiveLowerBoundSearchEngine().run(load_challenge())
    store = ControlStore(tmp_path / "control.db")
    store.record_lower_bound_search(report)
    loaded = store.get_lower_bound_search(report.run_id)
    assert loaded is not None
    assert loaded["status"] == "RESTRICTED_PROGRESS_WITH_OPEN_UNIVERSAL_TARGET"
    assert loaded["universal_status"] == "OPEN"
    assert loaded["payload"]["summary"]["restricted_query_certificate_valid"] is True
    assert len(store.list_lower_bound_searches(report.challenge_id)) == 1
