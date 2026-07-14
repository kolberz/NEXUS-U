from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core.models import ArtifactType, ResourceBudget, TaskMode, TaskSpec


class ConfigError(ValueError):
    pass


def task_from_dict(raw: dict[str, Any]) -> TaskSpec:
    required = {"intent", "artifact_type", "modes"}
    missing = required - raw.keys()
    if missing:
        raise ConfigError(f"Missing required keys: {sorted(missing)}")
    budget = ResourceBudget(**raw.get("budget", {}))
    return TaskSpec(
        intent=raw["intent"],
        artifact_type=ArtifactType(raw["artifact_type"]),
        modes=[TaskMode(item) for item in raw["modes"]],
        success_conditions=list(raw.get("success_conditions", [])),
        prohibited_shortcuts=list(raw.get("prohibited_shortcuts", [])),
        assumptions=list(raw.get("assumptions", [])),
        inputs=dict(raw.get("inputs", {})),
        adapter=raw.get("adapter", "document"),
        budget=budget,
        initial_obligations=list(raw.get("initial_obligations", [])),
        task_id=raw.get("task_id") or __import__("uuid").uuid4().hex,
    )


def load_task(path: Path | str) -> TaskSpec:
    return task_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
