from __future__ import annotations

from .base import AdapterResult
from nexus_u.core.models import Evidence, TaskSpec


class DocumentAdapter:
    name = "document"

    def construct(self, task: TaskSpec) -> AdapterResult:
        body = task.inputs.get("body") or task.intent
        output = {
            "title": task.inputs.get("title", "NEXUS-U Artifact"),
            "body": body,
            "format": task.inputs.get("format", "markdown"),
        }
        return AdapterResult(success=True, output=output, logs=["Document artifact constructed"])

    def execute(self, task: TaskSpec, constructed: AdapterResult) -> AdapterResult:
        rendered = constructed.output["body"].encode("utf-8")
        return AdapterResult(
            success=True,
            output={**constructed.output, "rendered_bytes": len(rendered)},
            evidence=[Evidence(kind="execution", summary="Document rendered in-memory")],
            logs=constructed.logs + ["Document execution completed"],
        )

    def verify(self, task: TaskSpec, executed: AdapterResult) -> AdapterResult:
        body = executed.output.get("body", "")
        missing = [condition for condition in task.success_conditions if condition.lower() not in body.lower()]
        success = not missing
        evidence = [Evidence(kind="execution", summary="Success-condition text checks completed")]
        obligations = [f"Missing success condition: {item}" for item in missing]
        return AdapterResult(success=success, output=executed.output, evidence=executed.evidence + evidence, obligations=obligations, logs=executed.logs + ["Document verification completed"])
