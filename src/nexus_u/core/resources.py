from __future__ import annotations

from dataclasses import dataclass
import os
import resource
import time

from .models import ResourceBudget


@dataclass(slots=True)
class ResourceSnapshot:
    elapsed_seconds: float
    peak_memory_mb: float
    output_bytes: int


class BudgetExceeded(RuntimeError):
    pass


class ResourceGuard:
    def __init__(self, budget: ResourceBudget) -> None:
        self.budget = budget
        self.started = time.monotonic()
        self._baseline_memory_mb = self._current_peak_memory_mb()

    def _current_peak_memory_mb(self) -> float:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        divisor = 1024 if os.name != "darwin" else 1024 * 1024
        return usage.ru_maxrss / divisor

    def snapshot(self, output_bytes: int = 0) -> ResourceSnapshot:
        elapsed = time.monotonic() - self.started
        memory_delta_mb = max(0.0, self._current_peak_memory_mb() - self._baseline_memory_mb)
        return ResourceSnapshot(elapsed, memory_delta_mb, output_bytes)

    def enforce(self, output_bytes: int = 0) -> ResourceSnapshot:
        snap = self.snapshot(output_bytes)
        if snap.elapsed_seconds > self.budget.wall_clock_seconds:
            raise BudgetExceeded("Wall-clock budget exceeded")
        if snap.peak_memory_mb > self.budget.memory_mb:
            raise BudgetExceeded("Memory budget exceeded")
        if snap.output_bytes > self.budget.output_bytes:
            raise BudgetExceeded("Output-size budget exceeded")
        return snap
