from __future__ import annotations

from nexus_u.benchmark.tension import run_tension_benchmark


def test_tension_benchmark_selects_discriminating_tests(tmp_path) -> None:
    report, path = run_tension_benchmark(output_dir=tmp_path)
    summary = report.summary()
    assert path.is_file()
    assert summary["case_count"] == 6
    assert summary["detection_rate"] == 1.0
    assert summary["experiment_match_rate"] == 1.0
    assert summary["static_baseline_rate"] == 0.0
    assert summary["tension_reduced_cases"] == 6
