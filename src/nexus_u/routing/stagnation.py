from __future__ import annotations

from typing import Any

from .models import StagnationReport


class StagnationDetector:
    def __init__(self, *, repeated_failure_threshold: int = 3) -> None:
        self.repeated_failure_threshold = max(2, repeated_failure_threshold)

    def detect(self, outcomes: list[dict[str, Any]]) -> StagnationReport:
        if not outcomes:
            return StagnationReport()
        ordered = sorted(outcomes, key=lambda item: float(item.get("created_at", 0)))
        recent = ordered[-6:]
        failures = [item for item in recent if not bool(item.get("success"))]
        if len(failures) < self.repeated_failure_threshold:
            return StagnationReport(failed_attempts=len(failures))

        tail = recent[-self.repeated_failure_threshold:]
        tail_strategies = [str(item.get("strategy")) for item in tail]
        if all(not bool(item.get("success")) for item in tail) and len(set(tail_strategies)) == 1:
            strategy = tail_strategies[0]
            return StagnationReport(
                detected=True,
                kind="REPEATED_FAILURE",
                failed_attempts=len(failures),
                repeated_strategies=[strategy],
                explanation=f"Strategy {strategy} failed {len(tail)} consecutive times.",
            )

        if len(recent) >= 4:
            last_four = [str(item.get("strategy")) for item in recent[-4:]]
            if (
                all(not bool(item.get("success")) for item in recent[-4:])
                and last_four[0] == last_four[2]
                and last_four[1] == last_four[3]
                and last_four[0] != last_four[1]
            ):
                return StagnationReport(
                    detected=True,
                    kind="OSCILLATION",
                    failed_attempts=len(failures),
                    repeated_strategies=sorted(set(last_four)),
                    explanation=f"Strategies {last_four[0]} and {last_four[1]} are oscillating without progress.",
                )

        no_progress = [item for item in recent if float(item.get("debt_delta", 0.0)) >= 0.0]
        if len(no_progress) >= self.repeated_failure_threshold and len(failures) >= self.repeated_failure_threshold:
            return StagnationReport(
                detected=True,
                kind="NO_DEBT_REDUCTION",
                failed_attempts=len(failures),
                repeated_strategies=sorted({str(item.get("strategy")) for item in no_progress}),
                explanation="Recent attempts failed to reduce weighted obligation debt.",
            )

        return StagnationReport(failed_attempts=len(failures))
