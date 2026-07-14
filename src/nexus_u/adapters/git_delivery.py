from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import AdapterResult
from nexus_u.core.models import Evidence, TaskSpec
from nexus_u.delivery.git_workspace import GitWorkspace, GitWorkspaceError


class GitDeliveryAdapter:
    name = "git_delivery"

    def construct(self, task: TaskSpec) -> AdapterResult:
        repository = task.inputs.get("repository")
        if not isinstance(repository, str) or not repository.strip():
            return AdapterResult(success=False, obligations=["inputs.repository must identify a local repository or source directory"])
        repo = Path(repository).expanduser().resolve()
        if not repo.exists() or not repo.is_dir():
            return AdapterResult(success=False, obligations=[f"Repository does not exist: {repo}"])
        changes = task.inputs.get("changes", {})
        patch = task.inputs.get("patch")
        if not isinstance(changes, dict):
            return AdapterResult(success=False, obligations=["inputs.changes must be an object mapping paths to complete file contents"])
        if not changes and not patch:
            return AdapterResult(success=False, obligations=["A Git delivery task requires inputs.changes or inputs.patch"])
        return AdapterResult(
            success=True,
            output={
                "repository": str(repo),
                "changes": {str(k): str(v) for k, v in changes.items()},
                "patch": patch,
                "delivery_contract": {
                    "test_commands": task.inputs.get("test_commands", []),
                    "security_commands": task.inputs.get("security_commands", []),
                    "build_commands": task.inputs.get("build_commands", []),
                    "required_paths": task.inputs.get("required_paths", []),
                    "forbidden_patterns": task.inputs.get("forbidden_patterns", []),
                    "required_patterns": task.inputs.get("required_patterns", []),
                    "rollback_required": bool(task.inputs.get("rollback_required", False)),
                    "rollback_command": task.inputs.get("rollback_command"),
                },
            },
            evidence=[Evidence(kind="construction", summary="Git delivery candidate and contract accepted")],
            logs=["Git delivery manifest normalized"],
        )

    def execute(self, task: TaskSpec, constructed: AdapterResult) -> AdapterResult:
        if not constructed.success:
            return constructed
        contract = constructed.output["delivery_contract"]
        workspace = GitWorkspace(constructed.output["repository"], timeout=task.budget.wall_clock_seconds)
        try:
            delivery = workspace.execute_delivery(
                changes=constructed.output.get("changes"),
                patch=constructed.output.get("patch"),
                command_groups={
                    "test": list(contract.get("test_commands", [])),
                    "security": list(contract.get("security_commands", [])),
                    "build": list(contract.get("build_commands", [])),
                },
                required_paths=contract.get("required_paths", []),
                forbidden_patterns=contract.get("forbidden_patterns", []),
                required_patterns=contract.get("required_patterns", []),
                rollback_required=bool(contract.get("rollback_required", False)),
                rollback_command=contract.get("rollback_command"),
            )
            raw = delivery.to_dict()
            # Preserve the temporary workspace through verify; verification removes it.
            raw["workspace_root"] = str(workspace._tmp) if delivery.success else None
            if not delivery.success:
                workspace.cleanup()
            obligation_results: list[dict[str, Any]] = []
            for result in delivery.commands:
                obligation_results.append({
                    "statement": f"{result.category.capitalize()} command succeeds: {' '.join(result.command)}",
                    "success": result.success,
                    "evidence_summary": f"{result.category} command returned {result.returncode}",
                    "kind": "TEST" if result.category == "test" else "POLICY",
                    "severity": "HIGH",
                })
            for check in delivery.checks:
                obligation_results.append({
                    "statement": f"Delivery check passes: {check['kind']} {check['target']}",
                    "success": bool(check["success"]),
                    "evidence_summary": f"{check['kind']} check {'passed' if check['success'] else 'failed'} for {check['target']}",
                    "kind": "POLICY",
                    "severity": "HIGH",
                })
            raw["obligation_results"] = obligation_results
            evidence = [
                Evidence(kind="execution", summary="Git-backed delivery workflow executed", metadata={"base_commit": delivery.base_commit}),
                Evidence(kind="execution", summary="Candidate Git diff recorded", sha256=delivery.diff_sha256, metadata={"changed_files": delivery.changed_files}),
            ]
            for result in delivery.commands:
                evidence.append(Evidence(
                    kind="execution",
                    summary=f"{result.category} command {'passed' if result.success else 'failed'}: {' '.join(result.command)}",
                    metadata=result.to_dict(),
                ))
            return AdapterResult(
                success=delivery.success,
                output=raw,
                evidence=evidence,
                obligations=list(delivery.obligations),
                logs=["Git workspace prepared", "Candidate changes applied", "Delivery checks executed"],
            )
        except GitWorkspaceError as exc:
            workspace.cleanup()
            return AdapterResult(success=False, output=constructed.output, obligations=[str(exc)], logs=["Git delivery execution failed"])

    def verify(self, task: TaskSpec, executed: AdapterResult) -> AdapterResult:
        output = dict(executed.output)
        obligations = list(executed.obligations)
        workspace_root = output.get("workspace_root")
        try:
            commands = output.get("commands", [])
            checks = output.get("checks", [])
            if any(not item.get("success", False) for item in commands):
                obligations.append("At least one declared delivery command failed")
            if any(not item.get("success", False) for item in checks):
                obligations.append("At least one declared delivery check failed")
            if not output.get("diff_sha256") or not output.get("changed_files"):
                obligations.append("Git change provenance is incomplete")
            success = executed.success and not obligations
            evidence = list(executed.evidence)
            if success:
                evidence.append(Evidence(
                    kind="execution",
                    summary="Git delivery contract passed",
                    sha256=output.get("diff_sha256"),
                    metadata={"base_commit": output.get("base_commit"), "changed_files": output.get("changed_files", [])},
                ))
            return AdapterResult(success=success, output=output, evidence=evidence, obligations=obligations, logs=executed.logs + ["Git delivery verification completed"])
        finally:
            if workspace_root:
                import shutil
                shutil.rmtree(workspace_root, ignore_errors=True)
