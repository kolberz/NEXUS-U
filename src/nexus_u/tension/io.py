from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nexus_u.federation import load_federation_spec

from .models import (
    DiscoveryHypothesis,
    DiscriminatingExperiment,
    HypothesisKind,
    ObservedExperimentResult,
)


def load_tension_spec(source: str | Path | dict[str, Any]):
    raw = source if isinstance(source, dict) else json.loads(Path(source).read_text(encoding="utf-8"))
    ledger, obligation_id, _ = load_federation_spec(raw)
    hypotheses: list[DiscoveryHypothesis] = []
    for item in raw.get("hypotheses", []):
        kwargs: dict[str, Any] = {
            "tension_id": str(item.get("tension_id", "pending")),
            "description": str(item["description"]),
            "kind": HypothesisKind(str(item["kind"])),
            "prior": float(item.get("prior", 0.25)),
            "complexity": float(item.get("complexity", 1.0)),
            "predicted_resolution": float(item.get("predicted_resolution", 0.5)),
            "new_obligations": [str(value) for value in item.get("new_obligations", [])],
            "assumptions": [str(value) for value in item.get("assumptions", [])],
            "metadata": dict(item.get("metadata", {})),
        }
        if item.get("hypothesis_id"):
            kwargs["hypothesis_id"] = str(item["hypothesis_id"])
        hypotheses.append(DiscoveryHypothesis(**kwargs))
    experiments: list[DiscriminatingExperiment] = []
    for item in raw.get("experiments", []):
        kwargs = {
            "description": str(item["description"]),
            "outcomes": [str(value) for value in item["outcomes"]],
            "likelihoods": {
                str(h): {str(o): float(p) for o, p in values.items()}
                for h, values in item["likelihoods"].items()
            },
            "cost": float(item.get("cost", 1.0)),
            "risk": float(item.get("risk", 0.0)),
            "prerequisites": [str(value) for value in item.get("prerequisites", [])],
            "metadata": dict(item.get("metadata", {})),
        }
        if item.get("experiment_id"):
            kwargs["experiment_id"] = str(item["experiment_id"])
        experiments.append(DiscriminatingExperiment(**kwargs))
    observed_raw = raw.get("observed_result")
    observed = None if not observed_raw else ObservedExperimentResult(
        experiment_id=str(observed_raw["experiment_id"]), outcome=str(observed_raw["outcome"])
    )
    return ledger, obligation_id, hypotheses, experiments, observed
