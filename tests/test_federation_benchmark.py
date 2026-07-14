from pathlib import Path

from nexus_u.benchmark.federation import run_federation_benchmark


def test_federation_benchmark_matches_all_expected_outcomes(tmp_path: Path):
    report, path = run_federation_benchmark(output_dir=tmp_path)
    assert path.is_file()
    summary = report.summary()
    assert summary["case_count"] == 6
    assert summary["expected_outcomes_matched"] == 6
    assert summary["match_rate"] == 1.0
