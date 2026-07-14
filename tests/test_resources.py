from __future__ import annotations

import pytest

from nexus_u.core.models import ResourceBudget
from nexus_u.core.resources import BudgetExceeded, ResourceGuard


def test_resource_guard_reports_nonnegative_memory() -> None:
    guard = ResourceGuard(ResourceBudget())
    snapshot = guard.snapshot()
    assert snapshot.peak_memory_mb >= 0


def test_resource_guard_enforces_output_budget() -> None:
    guard = ResourceGuard(ResourceBudget(output_bytes=3))
    with pytest.raises(BudgetExceeded, match="Output-size"):
        guard.enforce(output_bytes=4)


def test_resource_guard_enforces_memory_delta(monkeypatch) -> None:
    readings = iter((10.0, 12.0))
    monkeypatch.setattr(ResourceGuard, "_current_peak_memory_mb", lambda self: next(readings))
    guard = ResourceGuard(ResourceBudget(memory_mb=1))
    with pytest.raises(BudgetExceeded, match="Memory"):
        guard.enforce()
