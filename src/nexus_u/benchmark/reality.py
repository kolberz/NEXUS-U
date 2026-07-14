from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import time
from typing import Any

from nexus_u.config import task_from_dict
from nexus_u.core.pipeline import Pipeline
from nexus_u.delivery.git_workspace import GitWorkspace
from nexus_u.security.signing import write_signed_envelope


@dataclass(slots=True)
class BenchmarkCaseResult:
    case_id: str
    baseline_passed: bool
    nexus_released: bool
    expected_baseline: bool | None
    expected_nexus: bool | None
    hidden_obligation_caught: bool
    baseline_duration_seconds: float
    nexus_duration_seconds: float
    nexus_status: str
    artifact_id: str
    artifact_path: str
    obligation_summary: dict[str, Any] = field(default_factory=dict)
    obligation_metrics: dict[str, Any] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BenchmarkReport:
    suite: str
    started_at: float
    completed_at: float
    cases: list[BenchmarkCaseResult]

    def summary(self) -> dict[str, Any]:
        total = len(self.cases)
        baseline_passes = sum(item.baseline_passed for item in self.cases)
        nexus_releases = sum(item.nexus_released for item in self.cases)
        hidden = sum(item.hidden_obligation_caught for item in self.cases)
        expected_matches = sum(
            (item.expected_baseline is None or item.baseline_passed == item.expected_baseline)
            and (item.expected_nexus is None or item.nexus_released == item.expected_nexus)
            for item in self.cases
        )
        return {
            "case_count": total,
            "baseline_passes": baseline_passes,
            "nexus_releases": nexus_releases,
            "hidden_obligations_caught": hidden,
            "expected_outcomes_matched": expected_matches,
            "expected_outcome_rate": round(expected_matches / total, 4) if total else 0.0,
            "mean_baseline_seconds": round(sum(item.baseline_duration_seconds for item in self.cases) / total, 6) if total else 0.0,
            "mean_nexus_seconds": round(sum(item.nexus_duration_seconds for item in self.cases) / total, 6) if total else 0.0,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/reality-benchmark/v1",
            "suite": self.suite,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": self.summary(),
            "cases": [item.to_dict() for item in self.cases],
        }


class RealityBenchmark:
    def __init__(self, suite_path: str | Path, *, output_dir: str | Path) -> None:
        self.suite_path = Path(suite_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw = json.loads(self.suite_path.read_text(encoding="utf-8"))

    def _resolve_task(self, raw_task: dict[str, Any]) -> dict[str, Any]:
        data = json.loads(json.dumps(raw_task))
        repository = data.get("inputs", {}).get("repository")
        if repository:
            data["inputs"]["repository"] = str((self.suite_path.parent / repository).resolve())
        return data

    def _baseline(self, raw_task: dict[str, Any]) -> tuple[bool, float]:
        inputs = raw_task["inputs"]
        started = time.monotonic()
        workspace = GitWorkspace(inputs["repository"], timeout=float(raw_task.get("budget", {}).get("wall_clock_seconds", 30)))
        try:
            result = workspace.execute_delivery(
                changes=inputs.get("changes"),
                patch=inputs.get("patch"),
                command_groups={"test": list(inputs.get("test_commands", []))},
            )
            # Baseline deliberately considers only test execution, mirroring a
            # conventional prompt -> patch -> tests workflow.
            passed = all(item.success for item in result.commands) and bool(result.changed_files)
            return passed, time.monotonic() - started
        finally:
            workspace.cleanup()

    def run(self) -> BenchmarkReport:
        started = time.time()
        cases: list[BenchmarkCaseResult] = []
        artifacts_dir = self.output_dir / "artifacts"
        for raw_case in self.raw.get("cases", []):
            if os.environ.get("NEXUS_U_BENCHMARK_TRACE"):
                print(f"[benchmark] start {raw_case.get('id')}", flush=True)
            task_raw = self._resolve_task(raw_case["task"])
            baseline_passed, baseline_seconds = self._baseline(task_raw)
            if os.environ.get("NEXUS_U_BENCHMARK_TRACE"):
                print(f"[benchmark] baseline done {raw_case.get('id')}={baseline_passed}", flush=True)
            task = task_from_dict(task_raw)
            nexus_started = time.monotonic()
            record, artifact_path = Pipeline(output_dir=artifacts_dir).run(task)
            if os.environ.get("NEXUS_U_BENCHMARK_TRACE"):
                print(f"[benchmark] nexus done {raw_case.get('id')}={record.status}", flush=True)
            nexus_seconds = time.monotonic() - nexus_started
            hidden = baseline_passed and not record.released
            if os.environ.get("NEXUS_U_BENCHMARK_TRACE"):
                print(f"[benchmark] finish {raw_case.get('id')} baseline={baseline_passed} nexus={record.released}", flush=True)
            cases.append(BenchmarkCaseResult(
                case_id=str(raw_case["id"]),
                baseline_passed=baseline_passed,
                nexus_released=record.released,
                expected_baseline=raw_case.get("expected_baseline"),
                expected_nexus=raw_case.get("expected_nexus"),
                hidden_obligation_caught=hidden,
                baseline_duration_seconds=round(baseline_seconds, 6),
                nexus_duration_seconds=round(nexus_seconds, 6),
                nexus_status=str(record.status),
                artifact_id=record.artifact_id,
                artifact_path=str(artifact_path),
                obligation_summary=record.obligation_summary,
                obligation_metrics=record.obligation_metrics,
                unresolved=list(record.unresolved_obligations),
            ))
        return BenchmarkReport(str(self.raw.get("suite", self.suite_path.stem)), started, time.time(), cases)


def run_reality_benchmark(
    suite_path: str | Path,
    *,
    output_dir: str | Path,
    signing_secret: str | None = None,
    key_id: str = "reality-loop-local",
) -> tuple[BenchmarkReport, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report = RealityBenchmark(suite_path, output_dir=output).run()
    report_path = output / "reality-benchmark.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    if signing_secret:
        write_signed_envelope(report.to_dict(), output / "reality-benchmark.signed.json", key_id=key_id, secret=signing_secret)
    return report, report_path
