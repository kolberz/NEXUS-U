from __future__ import annotations

from .base import AdapterResult
from nexus_u.core.models import Evidence, TaskSpec
from nexus_u.discovery.evaluator import evaluate_candidates


class DiscoveryAdapter:
    name = "discovery"

    def construct(self, task: TaskSpec) -> AdapterResult:
        candidates = task.inputs.get("candidates")
        weights = task.inputs.get("weights")
        if not isinstance(candidates, list) or not candidates:
            return AdapterResult(success=False, obligations=["inputs.candidates must be a non-empty list"])
        if not isinstance(weights, dict) or not weights:
            return AdapterResult(success=False, obligations=["inputs.weights must be a non-empty object"])
        return AdapterResult(
            success=True,
            output={
                "candidates": candidates,
                "weights": weights,
                "constraints": task.inputs.get("constraints", {}),
                "minimum_score": float(task.inputs.get("minimum_score", float("-inf"))),
            },
            logs=["Discovery candidate set normalized"],
        )

    def execute(self, task: TaskSpec, constructed: AdapterResult) -> AdapterResult:
        if not constructed.success:
            return constructed
        result = evaluate_candidates(
            constructed.output["candidates"],
            weights=constructed.output["weights"],
            constraints=constructed.output["constraints"],
        )
        output = {**constructed.output, "discovery": result.to_dict()}
        evidence = [Evidence(kind="computation", summary="Candidates scored by deterministic evaluator")]
        return AdapterResult(
            success=result.winner is not None,
            output=output,
            evidence=evidence,
            obligations=[] if result.winner else ["No candidate satisfied declared constraints"],
            logs=constructed.logs + ["Discovery evaluation completed"],
        )

    def verify(self, task: TaskSpec, executed: AdapterResult) -> AdapterResult:
        obligations = list(executed.obligations)
        winner = executed.output.get("discovery", {}).get("winner")
        if winner is None:
            obligations.append("No winner available for promotion")
        elif float(winner["score"]) < float(executed.output["minimum_score"]):
            obligations.append("Winning candidate did not meet minimum score")
        success = executed.success and not obligations
        evidence = list(executed.evidence)
        if success:
            evidence.append(Evidence(kind="computation", summary="Winning candidate passed score and feasibility gates"))
        return AdapterResult(
            success=success,
            output=executed.output,
            evidence=evidence,
            obligations=obligations,
            logs=executed.logs + ["Discovery promotion gate completed"],
        )
