from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid
from typing import Any

PINNED_LEAN_TOOLCHAIN = "leanprover/lean4:v4.29.1"
PINNED_LEAN_VERSION = "4.29.1"
BRIDGE_THEOREM = "allSensitive_forces_allQueried"
UNIVERSAL_TARGET_STATUS = "OPEN"

LEAN_SOURCE = r'''/-
NEXUS-U v2.6 kernel-bridge theorem.

Scope: deterministic path certificates over finite Boolean inputs.
This theorem is deliberately generic. It proves that if every input coordinate is
sensitive at a witness and a deterministic path certificate is exact for all inputs
agreeing on its queried coordinates, then every coordinate was queried.

It does not prove the open offline multitape-Turing-machine Omega(n log n) lower bound.
-/
namespace NexusU.KernelBridge

abbrev BitInput (m : Nat) := Fin m → Bool

/-- Every coordinate selected by `queried` has value `true`. -/
def AllQueried {m : Nat} (queried : Fin m → Bool) : Prop :=
  ∀ i, queried i = true

/-- Coordinate `i` is sensitive at `x` if changing only `i` can change the output. -/
def SensitiveAt {m : Nat} {α : Type}
    (f : BitInput m → α) (x : BitInput m) (i : Fin m) : Prop :=
  ∃ y, (∀ j, j ≠ i → y j = x j) ∧ f y ≠ f x

/--
An exact deterministic path cannot omit a coordinate that is sensitive at the
witness: the sensitivity witness would preserve every queried answer, force the
same leaf/output, and contradict exactness.
-/
theorem allSensitive_forces_allQueried
    {m : Nat} {α : Type}
    (f : BitInput m → α)
    (x : BitInput m)
    (queried : Fin m → Bool)
    (pathExact : ∀ y, (∀ i, queried i = true → y i = x i) → f y = f x)
    (allSensitive : ∀ i, SensitiveAt f x i) :
    AllQueried queried := by
  intro i
  cases hQuery : queried i with
  | false =>
    obtain ⟨y, hSame, hDifferent⟩ := allSensitive i
    have hOutput : f y = f x := pathExact y (by
      intro j hQueried
      apply hSame j
      intro hEq
      subst j
      simp [hQuery] at hQueried)
    exact False.elim (hDifferent hOutput)
  | true =>
    rfl

/--
Conditional multiplication-facing specialization. A separate proof must establish
that the selected multiplication encoding is sensitive in all `2*n` coordinates.
-/
theorem exactMultiplicationPath_queriesEveryBit
    {n : Nat}
    (mulOutput : BitInput (2 * n) → Nat)
    (witness : BitInput (2 * n))
    (queried : Fin (2 * n) → Bool)
    (pathExact : ∀ y, (∀ i, queried i = true → y i = witness i) →
      mulOutput y = mulOutput witness)
    (allSensitive : ∀ i, SensitiveAt mulOutput witness i) :
    AllQueried queried :=
  allSensitive_forces_allQueried mulOutput witness queried pathExact allSensitive

end NexusU.KernelBridge
'''

LAKEFILE = '''name = "NexusUKernelBridge"\nversion = "0.1.0"\ndefaultTargets = ["NexusUKernelBridge"]\n\n[[lean_lib]]\nname = "NexusUKernelBridge"\n'''

LAKE_MANIFEST = '''{"version": "1.1.0",
 "packagesDir": ".lake/packages",
 "packages": [],
 "name": "NexusUKernelBridge",
 "lakeDir": ".lake"}
'''

ROOT_MODULE = "import NexusUKernelBridge.AllSensitive\n"

WORKFLOW = '''name: Lean kernel bridge\n\non:\n  push:\n  pull_request:\n  workflow_dispatch:\n\njobs:\n  kernel-check:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: leanprover/lean-action@v1\n        with:\n          lake-package-directory: formal/lean-kernel-bridge\n          auto-config: false\n      - name: Verify replay manifest inputs\n        run: python scripts/verify_kernel_bridge_manifest.py\n'''

VERIFY_SCRIPT = '''#!/usr/bin/env bash\nset -euo pipefail\ncd "$(dirname "$0")"\nlake build\n'''

FORBIDDEN_TOKENS = ("sorry", "admit", "axiom", "unsafe")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(slots=True)
class KernelExecution:
    attempted: bool
    available: bool
    trusted_identity: bool
    verified: bool
    status: str
    command: list[str] = field(default_factory=list)
    executable: str | None = None
    executable_sha256: str | None = None
    version_output: str = ""
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class KernelBridgeReport:
    project_id: str
    project_path: str
    toolchain: str
    theorem: str
    universal_target_status: str
    source_files: dict[str, str]
    static_checks: dict[str, Any]
    execution: KernelExecution
    replay_manifest_path: str
    replay_manifest_sha256: str
    status: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/kernel-verification-bridge/v1",
            "run_id": self.run_id,
            "created_at": self.created_at,
            "project_id": self.project_id,
            "project_path": self.project_path,
            "toolchain": self.toolchain,
            "theorem": self.theorem,
            "universal_target_status": self.universal_target_status,
            "source_files": self.source_files,
            "static_checks": self.static_checks,
            "execution": self.execution.to_dict(),
            "replay_manifest_path": self.replay_manifest_path,
            "replay_manifest_sha256": self.replay_manifest_sha256,
            "status": self.status,
        }


class KernelBridgeEngine:
    def __init__(self, *, explicit_lean: str | None = None, explicit_lake: str | None = None) -> None:
        self.explicit_lean = explicit_lean
        self.explicit_lake = explicit_lake

    @staticmethod
    def write_project(output_dir: str | Path) -> Path:
        root = Path(output_dir)
        source_dir = root / "NexusUKernelBridge"
        workflow_dir = root / ".github" / "workflows"
        source_dir.mkdir(parents=True, exist_ok=True)
        workflow_dir.mkdir(parents=True, exist_ok=True)
        (root / "lean-toolchain").write_text(PINNED_LEAN_TOOLCHAIN + "\n", encoding="utf-8")
        (root / "lakefile.toml").write_text(LAKEFILE, encoding="utf-8")
        (root / "lake-manifest.json").write_text(LAKE_MANIFEST, encoding="utf-8")
        (root / "NexusUKernelBridge.lean").write_text(ROOT_MODULE, encoding="utf-8")
        (source_dir / "AllSensitive.lean").write_text(LEAN_SOURCE, encoding="utf-8")
        verify = root / "verify.sh"
        verify.write_text(VERIFY_SCRIPT, encoding="utf-8")
        verify.chmod(0o755)
        (workflow_dir / "kernel-check.yml").write_text(WORKFLOW, encoding="utf-8")
        return root

    @staticmethod
    def static_check(project: Path) -> dict[str, Any]:
        lean_path = project / "NexusUKernelBridge" / "AllSensitive.lean"
        text = lean_path.read_text(encoding="utf-8")
        lowered = text.lower()
        forbidden = [token for token in FORBIDDEN_TOKENS if f"\n{token} " in lowered or f"\n{token}\n" in lowered]
        checks = {
            "lean_source_present": lean_path.is_file(),
            "theorem_present": f"theorem {BRIDGE_THEOREM}" in text,
            "multiplication_specialization_present": "theorem exactMultiplicationPath_queriesEveryBit" in text,
            "universal_solution_claim_absent": "Omega(n log n) lower bound is proved" not in text,
            "forbidden_declarations": forbidden,
            "balanced_parentheses": text.count("(") == text.count(")"),
            "balanced_brackets": text.count("[") == text.count("]"),
            "pinned_toolchain_present": (project / "lean-toolchain").read_text(encoding="utf-8").strip() == PINNED_LEAN_TOOLCHAIN,
            "lakefile_present": (project / "lakefile.toml").is_file(),
            "lake_manifest_present": (project / "lake-manifest.json").read_text(encoding="utf-8") == LAKE_MANIFEST,
            "root_module_present": (project / "NexusUKernelBridge.lean").read_text(encoding="utf-8") == ROOT_MODULE,
            "replay_script_present": (project / "verify.sh").is_file(),
            "ci_workflow_present": (project / ".github" / "workflows" / "kernel-check.yml").is_file(),
        }
        checks["passed"] = all(value for key, value in checks.items() if key != "forbidden_declarations") and not forbidden
        return checks

    def _locate(self) -> tuple[str | None, str | None]:
        # An explicitly selected executable must not be shadowed by another tool
        # discovered on PATH. This is also what makes deterministic test/replay
        # configurations possible on hosts that have both Lake and Lean installed.
        if self.explicit_lake:
            return self.explicit_lake, None
        if self.explicit_lean:
            return None, self.explicit_lean
        configured_lake = os.environ.get("NEXUS_U_LAKE")
        if configured_lake:
            return configured_lake, None
        configured_lean = os.environ.get("NEXUS_U_LEAN")
        if configured_lean:
            return None, configured_lean
        return shutil.which("lake"), shutil.which("lean")

    @staticmethod
    def _version(executable: str) -> tuple[str, bool]:
        try:
            result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=20, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            return str(exc), False
        output = (result.stdout + "\n" + result.stderr).strip()
        trusted = result.returncode == 0 and "Lean" in output and PINNED_LEAN_VERSION in output
        return output, trusted

    def execute(self, project: Path) -> KernelExecution:
        lake, lean = self._locate()
        executable = lake or lean
        if not executable:
            return KernelExecution(
                attempted=False,
                available=False,
                trusted_identity=False,
                verified=False,
                status="EXTERNAL_KERNEL_PENDING",
            )
        executable = str(Path(executable).resolve())
        version_output, trusted = self._version(executable)
        if lake:
            command = [executable, "build"]
        else:
            source = (project / "NexusUKernelBridge" / "AllSensitive.lean").resolve()
            command = [executable, str(source)]
        started = time.monotonic()
        try:
            result = subprocess.run(command, cwd=project, capture_output=True, text=True, timeout=180, check=False)
            duration = time.monotonic() - started
        except (OSError, subprocess.SubprocessError) as exc:
            return KernelExecution(
                attempted=True,
                available=True,
                trusted_identity=trusted,
                verified=False,
                status="KERNEL_EXECUTION_FAILED",
                command=command,
                executable=executable,
                executable_sha256=sha256_file(Path(executable)) if Path(executable).is_file() else None,
                version_output=version_output,
                stderr=str(exc),
                duration_seconds=time.monotonic() - started,
            )
        verified = trusted and result.returncode == 0
        return KernelExecution(
            attempted=True,
            available=True,
            trusted_identity=trusted,
            verified=verified,
            status="KERNEL_VERIFIED" if verified else ("UNTRUSTED_TOOLCHAIN" if not trusted else "KERNEL_REJECTED"),
            command=command,
            executable=executable,
            executable_sha256=sha256_file(Path(executable)) if Path(executable).is_file() else None,
            version_output=version_output,
            returncode=result.returncode,
            stdout=result.stdout[-20000:],
            stderr=result.stderr[-20000:],
            duration_seconds=duration,
        )

    @staticmethod
    def _manifest(project: Path, execution: KernelExecution) -> dict[str, Any]:
        files: dict[str, str] = {}
        for path in sorted(p for p in project.rglob("*") if p.is_file() and p.name != "replay-manifest.json"):
            files[str(path.relative_to(project))] = sha256_file(path)
        return {
            "schema": "https://nexus-u.dev/kernel-replay-manifest/v1",
            "project_id": "nexus-u-decision-tree-kernel-bridge",
            "toolchain": PINNED_LEAN_TOOLCHAIN,
            "theorem": BRIDGE_THEOREM,
            "files": files,
            "execution": execution.to_dict(),
            "universal_target_status": UNIVERSAL_TARGET_STATUS,
        }

    def run(self, output_dir: str | Path) -> KernelBridgeReport:
        project = self.write_project(output_dir)
        static = self.static_check(project)
        execution = self.execute(project) if static["passed"] else KernelExecution(
            attempted=False,
            available=bool(self._locate()[0] or self._locate()[1]),
            trusted_identity=False,
            verified=False,
            status="STATIC_CHECK_FAILED",
        )
        manifest = self._manifest(project, execution)
        manifest_path = project / "replay-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        source_files = dict(manifest["files"])
        if not static["passed"]:
            status = "BLOCKED"
        elif execution.verified:
            status = "KERNEL_VERIFIED"
        elif not execution.available:
            status = "PROOF_PROJECT_READY_KERNEL_PENDING"
        else:
            status = execution.status
        return KernelBridgeReport(
            project_id="nexus-u-decision-tree-kernel-bridge",
            project_path=str(project),
            toolchain=PINNED_LEAN_TOOLCHAIN,
            theorem=BRIDGE_THEOREM,
            universal_target_status=UNIVERSAL_TARGET_STATUS,
            source_files=source_files,
            static_checks=static,
            execution=execution,
            replay_manifest_path=str(manifest_path),
            replay_manifest_sha256=sha256_file(manifest_path),
            status=status,
        )
