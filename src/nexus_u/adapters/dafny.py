from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile

from .base import AdapterResult
from nexus_u.core.models import Evidence, TaskSpec
from nexus_u.integrations.commands import run_command


class DafnyAdapter:
    name = "dafny"

    def construct(self, task: TaskSpec) -> AdapterResult:
        source = task.inputs.get("source")
        if not isinstance(source, str) or not source.strip():
            return AdapterResult(success=False, obligations=["inputs.source must contain Dafny source"])
        return AdapterResult(
            success=True,
            output={
                "source": source,
                "file_name": str(task.inputs.get("file_name", "NexusArtifact.dfy")),
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            },
            logs=["Dafny source accepted"],
        )

    def execute(self, task: TaskSpec, constructed: AdapterResult) -> AdapterResult:
        if not constructed.success:
            return constructed
        dafny = shutil.which("dafny")
        if not dafny:
            return AdapterResult(
                success=False,
                output=constructed.output,
                obligations=["Dafny unavailable; install the Dafny CLI or use an external verification worker"],
                logs=constructed.logs + ["Dafny capability unavailable"],
            )
        project_dir_raw = task.inputs.get("project_dir")
        temp_context = tempfile.TemporaryDirectory(prefix="nexus-u-dafny-") if not project_dir_raw else None
        try:
            cwd = Path(project_dir_raw) if project_dir_raw else Path(temp_context.name)
            cwd.mkdir(parents=True, exist_ok=True)
            source_path = cwd / constructed.output["file_name"]
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text(constructed.output["source"], encoding="utf-8")
            result = run_command(
                [dafny, "verify", str(source_path.relative_to(cwd))],
                cwd=cwd,
                timeout=task.budget.wall_clock_seconds,
            )
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
                        kind="conditional_proof",
                        summary="Dafny verifier accepted implementation relative to its specifications",
                        verifier="Dafny",
                    )
                )
            return AdapterResult(
                success=result.returncode == 0,
                output=output,
                evidence=evidence,
                obligations=[] if result.returncode == 0 else ["Dafny verification failed or timed out"],
                logs=constructed.logs + ["Dafny verification command completed"],
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
            logs=executed.logs + ["Dafny evidence gate completed"],
        )
