from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any


def builtin_challenge_path() -> Path:
    return Path(str(files("nexus_u.lower_bounds").joinpath("data/integer-multiplication-challenge.json")))


def load_challenge(source: str | Path | dict[str, Any] | None = None) -> dict[str, Any]:
    if source is None:
        source = builtin_challenge_path()
    if isinstance(source, dict):
        return source
    return json.loads(Path(source).read_text(encoding="utf-8"))


def write_report(payload: dict[str, Any], output: str | Path) -> Path:
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return target
