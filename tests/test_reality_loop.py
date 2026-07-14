from __future__ import annotations

import json
import pytest
from pathlib import Path

from nexus_u.benchmark.reality import run_reality_benchmark
from nexus_u.config import task_from_dict
from nexus_u.core.pipeline import Pipeline


ROOT = Path(__file__).resolve().parents[1]


def _task(repository: Path, *, forbidden: bool = False, rollback: bool = True):
    inputs = {
        "repository": str(repository),
        "changes": {"calc.py": "def add(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return a * b\n"},
        "test_commands": ["python -m unittest discover -s tests -v"],
        "build_commands": ["python -m compileall -q ."],
        "required_patterns": [{"path": "calc.py", "pattern": "def multiply"}],
        "rollback_required": rollback,
        "rollback_command": "git reset --hard HEAD" if rollback else None,
    }
    if forbidden:
        inputs["forbidden_patterns"] = [{"path": "calc.py", "pattern": "multiply"}]
    return task_from_dict({
        "intent": "Deliver a Git-backed calculator change",
        "artifact_type": "software",
        "modes": ["SOFTWARE_ENGINEERING"],
        "adapter": "git_delivery",
        "success_conditions": ["All declared Git delivery checks pass"],
        "inputs": inputs,
        "budget": {"wall_clock_seconds": 20, "memory_mb": 512, "output_bytes": 1000000},
    })


def test_git_delivery_releases_good_candidate(tmp_path: Path):
    task = _task(ROOT / "benchmarks/fixtures/good")
    record, _ = Pipeline(output_dir=tmp_path).run(task)
    assert record.released
    assert record.output["diff_sha256"]
    assert record.obligation_metrics["resolution_ratio"] > 0.8


def test_git_delivery_blocks_failed_contract(tmp_path: Path):
    task = _task(ROOT / "benchmarks/fixtures/good", forbidden=True)
    record, _ = Pipeline(output_dir=tmp_path).run(task)
    assert not record.released
    assert any("forbidden_pattern" in item for item in record.unresolved_obligations)
    assert record.obligation_summary["blocking_unresolved_count"] > 0


@pytest.mark.reality
def test_reality_benchmark_catches_hidden_obligations(tmp_path: Path):
    report, report_path = run_reality_benchmark(
        ROOT / "benchmarks/cases/reality_suite.json",
        output_dir=tmp_path,
        signing_secret="test-secret",
    )
    assert report_path.exists()
    assert (tmp_path / "reality-benchmark.signed.json").exists()
    summary = report.summary()
    assert summary["case_count"] == 4
    assert summary["baseline_passes"] == 4
    assert summary["hidden_obligations_caught"] == 3
    assert summary["expected_outcome_rate"] == 1.0
    payload = json.loads(report_path.read_text())
    assert payload["summary"]["nexus_releases"] == 1
