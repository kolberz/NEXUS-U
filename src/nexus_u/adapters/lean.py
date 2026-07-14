from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile

from .base import AdapterResult
from nexus_u.core.models import Evidence, TaskSpec
from nexus_u.integrations.commands import run_command


_FORBIDDEN = ("sorry", "admit")


class LeanAdapter:
    name = "lean"

    def construct(self, task: TaskSpec) -> AdapterResult:
        source = task.inputs.get("source")
        if not isinstance(source, str) or not source.strip():
            return AdapterResult(success=False, obligations=["inputs.source must contain Lean source"])
        lower = source.lower()
        forbidden = [token for token in _FORBIDDEN if token in lower]
        if forbidden:
            return AdapterResult(success=False, obligations=[f"Forbidden Lean placeholder detected: {token}" for token in forbidden])
        if "axiom " in lower and not bool(task.inputs.get("allow_axioms", False)):
            return AdapterResult(success=False, obligations=["Lean source introduces an axiom; set allow_axioms only after trust review"])
        return AdapterResult(
            success=True,
            output={
                "source": source,
                "file_name": str(task.inputs.get("file_name", "NexusArtifact.lean")),
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            },
            logs=["Lean source passed trust preflight"],
        )

    def execute(self, task: TaskSpec, constructed: AdapterResult) -> AdapterResult:
        if not constructed.success:
            return constructed
        lean = shutil.which("lean")
        lake = shutil.which("lake")
        if not lean and not lake:
            return AdapterResult(
                success=False,
                output=constructed.output,
                obligations=["Lean toolchain unavailable; install elan/Lean or use an external proof worker"],
                logs=constructed.logs + ["Lean capability unavailable"],
            )
        project_dir_raw = task.inputs.get("project_dir")
        temp_context = tempfile.TemporaryDirectory(prefix="nexus-u-lean-") if not project_dir_raw else None
        try:
            cwd = Path(project_dir_raw) if project_dir_raw else Path(temp_context.name)
            cwd.mkdir(parents=True, exist_ok=True)
            source_path = cwd / constructed.output["file_name"]
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text(constructed.output["source"], encoding="utf-8")
            relative = str(source_path.relative_to(cwd))
            if lake and ((cwd / "lakefile.toml").exists() or (cwd / "lakefile.lean").exists()):
                command = [lake, "env", "lean", relative]
            elif lean:
                command = [lean, relative]
            else:
                command = [lake, "env", "lean", relative]
            result = run_command(command, cwd=cwd, timeout=task.budget.wall_clock_seconds)
            output = {
                **constructed.output,
                "command": list(result.command),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timed_out": result.timed_out,
            }
            evidence = []
            if result.returncode == 0:
                evidence.append(
                    Evidence(
                        kind="kernel",
                        summary="Lean accepted source without prohibited placeholders",
                        verifier="Lean",
                        metadata={"command": list(result.command)},
                    )
                )
            obligations = [] if result.returncode == 0 else ["Lean verification failed or timed out"]
            return AdapterResult(
                success=result.returncode == 0,
                output=output,
                evidence=evidence,
                obligations=obligations,
                logs=constructed.logs + ["Lean verification command completed"],
            )
        finally:
            if temp_context:
                temp_context.cleanup()

    def verify(self, task: TaskSpec, executed: AdapterResult) -> AdapterResult:
        return AdapterResult(
            success=executed.success,
            output=executed.output,
            evidence=list(executed.evidence),
            obligations=list(executed.obligations),
            logs=executed.logs + ["Lean evidence gate completed"],
        )
