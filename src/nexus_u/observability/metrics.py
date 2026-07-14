from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
import time
from typing import Any


@dataclass(slots=True)
class Event:
    timestamp: float
    name: str
    fields: dict[str, Any]


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._events: deque[Event] = deque(maxlen=1000)

    @staticmethod
    def _key(name: str, labels: dict[str, Any] | None = None) -> tuple[str, tuple[tuple[str, str], ...]]:
        return name, tuple(sorted((str(k), str(v)) for k, v in (labels or {}).items()))

    def inc(self, name: str, amount: float = 1.0, **labels: Any) -> None:
        with self._lock:
            self._counters[self._key(name, labels)] += amount

    def set_gauge(self, name: str, value: float, **labels: Any) -> None:
        with self._lock:
            self._gauges[self._key(name, labels)] = value

    def event(self, name: str, **fields: Any) -> None:
        with self._lock:
            self._events.append(Event(time.time(), name, fields))

    def recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            events = list(self._events)[-max(0, min(limit, 1000)):]
        return [{"timestamp": e.timestamp, "name": e.name, "fields": e.fields} for e in events]

    def prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            counters = dict(self._counters)
            gauges = dict(self._gauges)
        for (name, labels), value in sorted({**counters, **gauges}.items()):
            suffix = ""
            if labels:
                escaped = [f'{k}="{v.replace(chr(34), chr(92)+chr(34))}"' for k, v in labels]
                suffix = "{" + ",".join(escaped) + "}"
            lines.append(f"{name}{suffix} {value}")
        return "\n".join(lines) + "\n"


METRICS = MetricsRegistry()
