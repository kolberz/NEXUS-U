from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from nexus_u.tension.models import TensionKind

from .models import CorpusClaim, TrialCase, TrialExpectation


def _claim(raw: dict[str, Any], case_id: str) -> CorpusClaim:
    return CorpusClaim(
        case_id=case_id,
        claim_id=str(raw["claim_id"]),
        topic=str(raw.get("topic", case_id)),
        statement=str(raw["statement"]),
        verdict=str(raw["verdict"]).upper(),
        source_id=str(raw["source_id"]),
        source_title=str(raw.get("source_title", raw["source_id"])),
        organization_id=str(raw.get("organization_id", raw["source_id"])),
        provenance_group=str(raw.get("provenance_group", raw["source_id"])),
        evidence_kind=str(raw.get("evidence_kind", "document_claim")),
        trust_weight=float(raw.get("trust_weight", 1.0)),
        scope=str(raw.get("scope", "global")),
        tension_kind=TensionKind(str(raw.get("tension_kind", TensionKind.CONTRADICTION.value))),
        metadata=dict(raw.get("metadata", {})),
    )


def load_trial_suite(source: str | Path | dict[str, Any]) -> tuple[str, list[TrialCase], dict[str, Any]]:
    raw = source if isinstance(source, dict) else json.loads(Path(source).read_text(encoding="utf-8"))
    cases: list[TrialCase] = []
    for case_raw in raw.get("cases", []):
        case_id = str(case_raw["case_id"])
        expected_kind = case_raw.get("expected_kind")
        cases.append(TrialCase(
            case_id=case_id,
            title=str(case_raw.get("title", case_id)),
            expectation=TrialExpectation(str(case_raw.get("expectation", TrialExpectation.TENSION.value))),
            expected_kind=TensionKind(str(expected_kind)) if expected_kind else None,
            claims=[_claim(item, case_id) for item in case_raw.get("claims", [])],
            expected_experiment_terms=[str(item).lower() for item in case_raw.get("expected_experiment_terms", [])],
            notes=str(case_raw.get("notes", "")),
        ))
    return str(raw.get("suite_id", "discovery-trials")), cases, dict(raw.get("metadata", {}))


def claims_from_csv(path: str | Path) -> list[CorpusClaim]:
    result: list[CorpusClaim] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            metadata_raw = raw.pop("metadata", "") or "{}"
            raw["metadata"] = json.loads(metadata_raw)
            result.append(_claim(raw, str(raw["case_id"])))
    return result


def corpus_digest(cases: list[TrialCase]) -> str:
    payload = json.dumps(
        [case.to_dict(include_expectation=False) for case in cases],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
