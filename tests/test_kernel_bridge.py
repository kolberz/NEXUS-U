from __future__ import annotations

import json
import os
from pathlib import Path

from nexus_u.benchmark.kernel_bridge import run_kernel_bridge_benchmark
from nexus_u.formalization.kernel_bridge import KernelBridgeEngine, PINNED_LEAN_TOOLCHAIN
from nexus_u.storage.sqlite import ControlStore


def _fake_lean(tmp_path: Path, version: str) -> Path:
    if os.name == "nt":
        fake = tmp_path / "lean.cmd"
        fake.write_text(
            "@echo off\n"
            f'if "%~1"=="--version" (echo {version}& exit /b 0)\n'
            'if exist "%~1" (exit /b 0)\n'
            "exit /b 1\n",
            encoding="utf-8",
        )
    else:
        fake = tmp_path / "lean"
        fake.write_text(
            "#!/bin/sh\n"
            f'if [ "$1" = "--version" ]; then echo \'{version}\'; exit 0; fi\n'
            'test -f "$1"\n',
            encoding="utf-8",
        )
        fake.chmod(0o755)
    return fake


def test_kernel_bridge_generates_replayable_project(tmp_path: Path) -> None:
    report = KernelBridgeEngine(explicit_lean="/definitely/missing/lean").run(tmp_path / "project")
    # An explicit missing path is attempted and rejected, not converted into proof success.
    assert report.static_checks["passed"] is True
    assert report.universal_target_status == "OPEN"
    assert report.execution.verified is False
    assert Path(report.replay_manifest_path).is_file()
    assert (tmp_path / "project" / "lean-toolchain").read_text().strip() == PINNED_LEAN_TOOLCHAIN
    assert json.loads((tmp_path / "project" / "lake-manifest.json").read_text())["packages"] == []
    assert (tmp_path / "project" / "NexusUKernelBridge.lean").read_text().strip() == "import NexusUKernelBridge.AllSensitive"


def test_kernel_bridge_unavailable_is_explicit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)
    report = KernelBridgeEngine().run(tmp_path / "project")
    assert report.status == "PROOF_PROJECT_READY_KERNEL_PENDING"
    assert report.execution.status == "EXTERNAL_KERNEL_PENDING"
    assert report.execution.available is False
    assert report.execution.verified is False


def test_kernel_bridge_rejects_untrusted_fake_toolchain(tmp_path: Path) -> None:
    fake = _fake_lean(tmp_path, "fake")
    report = KernelBridgeEngine(explicit_lean=str(fake)).run(tmp_path / "project")
    assert report.execution.available is True
    assert report.execution.trusted_identity is False
    assert report.execution.verified is False
    assert report.status == "UNTRUSTED_TOOLCHAIN"


def test_kernel_bridge_runner_accepts_pinned_identity_in_mechanical_test(tmp_path: Path) -> None:
    fake = _fake_lean(tmp_path, "Lean (version 4.29.1, test-platform)")
    report = KernelBridgeEngine(explicit_lean=str(fake)).run(tmp_path / "project")
    assert report.execution.trusted_identity is True
    assert report.execution.verified is True
    assert report.status == "KERNEL_VERIFIED"
    # This test validates orchestration only; the production benchmark never injects this fake tool.


def test_kernel_bridge_resolves_source_for_relative_output_path(tmp_path: Path, monkeypatch) -> None:
    fake = _fake_lean(tmp_path, "Lean (version 4.29.1, test-platform)")
    monkeypatch.chdir(tmp_path)
    report = KernelBridgeEngine(explicit_lean=str(fake)).run(Path("relative-project"))
    assert Path(report.execution.command[1]).is_absolute()
    assert report.execution.verified is True


def test_kernel_bridge_static_check_detects_forbidden_declaration(tmp_path: Path) -> None:
    project = KernelBridgeEngine.write_project(tmp_path / "project")
    source = project / "NexusUKernelBridge" / "AllSensitive.lean"
    source.write_text(source.read_text() + "\naxiom fabricated : False\n")
    checks = KernelBridgeEngine.static_check(project)
    assert checks["passed"] is False
    assert "axiom" in checks["forbidden_declarations"]


def test_kernel_bridge_benchmark_and_storage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)
    benchmark, path = run_kernel_bridge_benchmark(output_dir=tmp_path / "out")
    assert benchmark.summary()["pass_rate"] == 1.0
    assert path.is_file()
    store = ControlStore(tmp_path / "control.db")
    store.record_kernel_bridge(benchmark.bridge_report)
    stored = store.get_kernel_bridge(benchmark.bridge_report.run_id)
    assert stored is not None
    assert stored["status"] == "PROOF_PROJECT_READY_KERNEL_PENDING"
    assert len(store.list_kernel_bridges()) == 1
    raw = json.loads(path.read_text())
    assert raw["summary"]["universal_status"] == "OPEN"
