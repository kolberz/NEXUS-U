from __future__ import annotations

from nexus_u.core.models import TaskMode, TaskSpec


_MODE_STEPS: dict[TaskMode, tuple[str, ...]] = {
    TaskMode.FORMAL_PROOF: ("formalize", "counterexample_search", "proof_search", "kernel_check"),
    TaskMode.SOFTWARE_ENGINEERING: ("contract", "construct", "execute", "test", "provenance"),
    TaskMode.SCIENTIFIC_MODELING: ("model", "simulate", "sensitivity", "evidence_review"),
    TaskMode.EXPERIMENTAL_RESEARCH: ("hypothesize", "evaluate", "falsify", "reproduce"),
    TaskMode.CONTROL_SYNTHESIS: ("dynamics", "safety_constraint", "controller", "runtime_monitor"),
    TaskMode.SYSTEM_ARCHITECTURE: ("interfaces", "dependencies", "risk_composition", "deployment"),
    TaskMode.DATA_ANALYSIS: ("schema", "quality", "analysis", "reproduction"),
    TaskMode.CREATIVE_CONSTRUCTION: ("generate", "fit_gate", "local_repair", "release"),
    TaskMode.RESOURCE_CONSTRAINED_DEPLOYMENT: ("resource_contract", "lower", "residual_cost", "deploy"),
    TaskMode.POLICY_AND_COMPLIANCE: ("policy", "monitor", "evidence", "human_authority"),
}


def build_workflow_plan(task: TaskSpec) -> dict[str, object]:
    steps: list[str] = []
    for mode in task.modes:
        for step in _MODE_STEPS[mode]:
            if step not in steps:
                steps.append(step)
    return {
        "task_id": task.task_id,
        "adapter": task.adapter,
        "modes": [str(mode) for mode in task.modes],
        "steps": steps,
        "release_policy": "evidence_capped",
    }
