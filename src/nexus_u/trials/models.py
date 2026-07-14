from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import time
from typing import Any
import uuid

from nexus_u.tension.models import TensionKind


class TrialExpectation(StrEnum):
    TENSION = "TENSION"
    NO_TENSION = "NO_TENSION"


@dataclass(slots=True)
class CorpusClaim:
    case_id: str
    claim_id: str
    topic: str
    statement: str
    verdict: str
    source_id: str
    source_title: str
    organization_id: str
    provenance_group: str
    evidence_kind: str = "document_claim"
    trust_weight: float = 1.0
    scope: str = "global"
    tension_kind: TensionKind = TensionKind.CONTRADICTION
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["tension_kind"] = self.tension_kind.value
        return raw


@dataclass(slots=True)
class TrialCase:
    case_id: str
    title: str
    expectation: TrialExpectation
    expected_kind: TensionKind | None
    claims: list[CorpusClaim]
    expected_experiment_terms: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self, *, include_expectation: bool = True) -> dict[str, Any]:
        raw = {
            "case_id": self.case_id,
            "title": self.title,
            "claims": [claim.to_dict() for claim in self.claims],
            "notes": self.notes,
        }
        if include_expectation:
            raw.update({
                "expectation": self.expectation.value,
                "expected_kind": self.expected_kind.value if self.expected_kind else None,
                "expected_experiment_terms": list(self.expected_experiment_terms),
            })
        return raw


@dataclass(slots=True)
class TrialCaseResult:
    case_id: str
    expected: TrialExpectation
    predicted_tension: bool
    expected_kind: str | None
    predicted_kind: str | None
    kind_match: bool
    experiment_match: bool
    false_discovery: bool
    missed_tension: bool
    abstained_correctly: bool
    tension_score: float
    recommended_experiment: str | None
    source_count: int
    provenance_groups: int
    report: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DiscoveryTrialReport:
    suite_id: str
    cases: list[TrialCaseResult]
    corpus_hash: str
    engine_version: str
    metadata: dict[str, Any] = field(default_factory=dict)
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def summary(self) -> dict[str, Any]:
        positives = sum(1 for case in self.cases if case.expected == TrialExpectation.TENSION)
        negatives = len(self.cases) - positives
        tp = sum(1 for case in self.cases if case.expected == TrialExpectation.TENSION and case.predicted_tension)
        fp = sum(1 for case in self.cases if case.expected == TrialExpectation.NO_TENSION and case.predicted_tension)
        fn = sum(1 for case in self.cases if case.expected == TrialExpectation.TENSION and not case.predicted_tension)
        tn = sum(1 for case in self.cases if case.expected == TrialExpectation.NO_TENSION and not case.predicted_tension)
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0
        specificity = tn / (tn + fp) if tn + fp else 1.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        kind_matches = sum(1 for case in self.cases if case.expected == TrialExpectation.TENSION and case.kind_match)
        experiment_matches = sum(1 for case in self.cases if case.expected == TrialExpectation.TENSION and case.experiment_match)
        return {
            "case_count": len(self.cases),
            "positive_cases": positives,
            "negative_controls": negatives,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "specificity": round(specificity, 6),
            "f1": round(f1, 6),
            "kind_matches": kind_matches,
            "experiment_matches": experiment_matches,
            "correct_abstentions": sum(1 for case in self.cases if case.abstained_correctly),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/discovery-trials/v1",
            "run_id": self.run_id,
            "created_at": self.created_at,
            "suite_id": self.suite_id,
            "corpus_hash": self.corpus_hash,
            "engine_version": self.engine_version,
            "metadata": self.metadata,
            "summary": self.summary(),
            "cases": [case.to_dict() for case in self.cases],
        }
