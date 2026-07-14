from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from nexus_u.external_challenge.engine import IndependentDiscoveryChallengeRunner
from nexus_u.external_challenge.models import ExternalCase, ExternalClaim


def _case(raw: dict) -> ExternalCase:
    return ExternalCase(
        case_id=str(raw["case_id"]),
        title=str(raw.get("title", raw["case_id"])),
        claims=[ExternalClaim(**item) for item in raw.get("claims", [])],
        source_ids=[str(v) for v in raw.get("source_ids", [])],
        notes=str(raw.get("notes", "")),
    )


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python -m nexus_u.reproduction.worker INPUT OUTPUT", file=sys.stderr)
        return 2
    source = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    runner = IndependentDiscoveryChallengeRunner()
    predictions = [runner.infer(_case(item)) for item in source["cases"]]
    output = {
        "evaluator_id": source["evaluator_id"],
        "process_id": os.getpid(),
        "predictions": predictions,
    }
    Path(sys.argv[2]).write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
