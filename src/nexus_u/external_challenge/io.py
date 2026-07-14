from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from nexus_u.tension.models import TensionKind

from .models import DatasetSource, ExternalCase, ExternalClaim, ExternalLabel


def digest_payload(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def load_source_registry(path: str | Path) -> tuple[list[DatasetSource], dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    sources = [DatasetSource(**item) for item in raw.get("sources", [])]
    return sources, dict(raw.get("metadata", {}))


def load_external_corpus(path: str | Path) -> tuple[str, list[ExternalCase], dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    cases: list[ExternalCase] = []
    for item in raw.get("cases", []):
        claims = [ExternalClaim(**claim) for claim in item.get("claims", [])]
        cases.append(ExternalCase(
            case_id=str(item["case_id"]),
            title=str(item.get("title", item["case_id"])),
            claims=claims,
            source_ids=[str(v) for v in item.get("source_ids", [])],
            notes=str(item.get("notes", "")),
        ))
    return str(raw.get("challenge_id", "independent-discovery-challenge")), cases, dict(raw.get("metadata", {}))


def load_external_labels(path: str | Path) -> dict[str, ExternalLabel]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    result: dict[str, ExternalLabel] = {}
    for item in raw.get("labels", []):
        kind = item.get("expected_kind")
        label = ExternalLabel(
            case_id=str(item["case_id"]),
            expected_tension=bool(item["expected_tension"]),
            expected_kind=TensionKind(str(kind)) if kind else None,
            expected_experiment_terms=[str(v).lower() for v in item.get("expected_experiment_terms", [])],
        )
        result[label.case_id] = label
    return result


def corpus_hash(cases: list[ExternalCase]) -> str:
    return digest_payload([case.to_dict() for case in cases])
