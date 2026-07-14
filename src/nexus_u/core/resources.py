from __future__ import annotations

from dataclasses import dataclass
import os
import time

try:
    import resource as _resource
except ImportError:  # pragma: no cover - exercised on Windows
    _resource = None

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
        if _resource is not None:
            usage = _resource.getrusage(_resource.RUSAGE_SELF)
            divisor = 1024 if os.name != "darwin" else 1024 * 1024
            return usage.ru_maxrss / divisor
        if os.name == "nt":
            return _windows_peak_working_set_mb()
        return 0.0

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


def _windows_peak_working_set_mb() -> float:
    """Return this process's peak working set using the Windows process API."""
    import ctypes
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    if not psapi.GetProcessMemoryInfo(
        kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.PeakWorkingSetSize / (1024 * 1024)
