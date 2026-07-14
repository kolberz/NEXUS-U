from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from .base import AdapterResult
from nexus_u.core.models import Evidence, TaskSpec


class PythonExecutionAdapter:
    name = "python"

    def construct(self, task: TaskSpec) -> AdapterResult:
        code = task.inputs.get("code")
        if not isinstance(code, str) or not code.strip():
            return AdapterResult(success=False, obligations=["inputs.code must contain Python source"])
        digest = hashlib.sha256(code.encode()).hexdigest()
        return AdapterResult(success=True, output={"code": code, "source_sha256": digest}, logs=["Python source accepted"])

    def execute(self, task: TaskSpec, constructed: AdapterResult) -> AdapterResult:
        if not constructed.success:
            return constructed
        with tempfile.TemporaryDirectory(prefix="nexus-u-") as tmp:
            path = Path(tmp) / "artifact.py"
            path.write_text(constructed.output["code"], encoding="utf-8")
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", str(path)],
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                    timeout=task.budget.wall_clock_seconds,
                    env={"PYTHONHASHSEED": "0"},
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                return AdapterResult(success=False, output=constructed.output, obligations=["Execution timed out"], logs=[str(exc)])

        output = {
            **constructed.output,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
        evidence = [Evidence(kind="execution", summary="Python process executed", metadata={"returncode": proc.returncode})]
        return AdapterResult(success=proc.returncode == 0, output=output, evidence=evidence, logs=["Python execution completed"])

    def verify(self, task: TaskSpec, executed: AdapterResult) -> AdapterResult:
        obligations = list(executed.obligations)
        for condition in task.success_conditions:
            if condition not in executed.output.get("stdout", ""):
                obligations.append(f"Expected stdout token not found: {condition}")
        success = executed.success and not obligations
        evidence = list(executed.evidence)
        if success:
            evidence.append(Evidence(kind="execution", summary="Execution and output assertions passed"))
        return AdapterResult(success=success, output=executed.output, evidence=evidence, obligations=obligations, logs=executed.logs + ["Python verification completed"])
