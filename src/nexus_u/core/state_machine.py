from __future__ import annotations

from .models import RunStatus


ALLOWED: dict[RunStatus, set[RunStatus]] = {
    RunStatus.INTAKE: {RunStatus.INTENT_COMPILED, RunStatus.REJECTED},
    RunStatus.INTENT_COMPILED: {RunStatus.ASSUMPTIONS_EXPOSED, RunStatus.REJECTED},
    RunStatus.ASSUMPTIONS_EXPOSED: {RunStatus.TARGET_FORMALIZED, RunStatus.REJECTED},
    RunStatus.TARGET_FORMALIZED: {RunStatus.CANDIDATES_GENERATED, RunStatus.REJECTED},
    RunStatus.CANDIDATES_GENERATED: {RunStatus.FALSIFICATION, RunStatus.REJECTED},
    RunStatus.FALSIFICATION: {RunStatus.REFUTED, RunStatus.OBSTRUCTION_CLASSIFIED},
    RunStatus.OBSTRUCTION_CLASSIFIED: {RunStatus.STRATEGY_ROUTED, RunStatus.UNKNOWN},
    RunStatus.STRATEGY_ROUTED: {RunStatus.ARTIFACT_CONSTRUCTED, RunStatus.PARTIAL, RunStatus.REJECTED},
    RunStatus.ARTIFACT_CONSTRUCTED: {RunStatus.EXECUTED, RunStatus.PARTIAL, RunStatus.REJECTED},
    RunStatus.EXECUTED: {RunStatus.VERIFIED, RunStatus.PARTIAL, RunStatus.REJECTED},
    RunStatus.VERIFIED: {RunStatus.POLICY_REVIEWED, RunStatus.PARTIAL, RunStatus.REJECTED},
    RunStatus.POLICY_REVIEWED: {RunStatus.SAFETY_REVIEWED, RunStatus.PARTIAL, RunStatus.REJECTED},
    RunStatus.SAFETY_REVIEWED: {RunStatus.ADVERSARIAL_REVIEWED, RunStatus.PARTIAL, RunStatus.REJECTED},
    RunStatus.ADVERSARIAL_REVIEWED: {RunStatus.CERTIFIED, RunStatus.PARTIAL, RunStatus.REJECTED},
    RunStatus.CERTIFIED: {RunStatus.CURATED},
    RunStatus.CURATED: {RunStatus.RELEASED},
    RunStatus.RELEASED: set(),
    RunStatus.PARTIAL: set(),
    RunStatus.REJECTED: set(),
    RunStatus.REFUTED: set(),
    RunStatus.UNKNOWN: set(),
}


class InvalidTransition(RuntimeError):
    pass


def transition(current: RunStatus, target: RunStatus) -> RunStatus:
    if target not in ALLOWED[current]:
        raise InvalidTransition(f"Invalid transition: {current} -> {target}")
    return target
