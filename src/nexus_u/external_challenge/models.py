from __future__ import annotations

from dataclasses import asdict, dataclass, field
import time
from typing import Any
import uuid

from nexus_u.tension.models import TensionKind


@dataclass(slots=True)
class DatasetSource:
    source_id: str
    title: str
    homepage: str
    citation: str
    license: str
    version: str
    snapshot_method: str
    upstream_record_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExternalClaim:
    claim_id: str
    statement: str
    verdict: str
    source_id: str
    organization_id: str
    provenance_group: str
    source_title: str = ""
    evidence_kind: str = "external_dataset_annotation"
    trust_weight: float = 1.0
    scope: str = "external-benchmark"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExternalCase:
    case_id: str
    title: str
    claims: list[ExternalClaim]
    source_ids: list[str]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExternalLabel:
    case_id: str
    expected_tension: bool
    expected_kind: TensionKind | None = None
    expected_experiment_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["expected_kind"] = self.expected_kind.value if self.expected_kind else None
        return raw


@dataclass(slots=True)
class ExternalCaseResult:
    case_id: str
    expected_tension: bool
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
    report: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExternalChallengeReport:
    challenge_id: str
    cases: list[ExternalCaseResult]
    corpus_hash: str
    labels_hash: str
    source_registry_hash: str
    engine_version: str
    label_firewall_verified: bool
    metadata: dict[str, Any] = field(default_factory=dict)
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def summary(self) -> dict[str, Any]:
        positives = sum(1 for case in self.cases if case.expected_tension)
        negatives = len(self.cases) - positives
        tp = sum(1 for case in self.cases if case.expected_tension and case.predicted_tension)
        fp = sum(1 for case in self.cases if not case.expected_tension and case.predicted_tension)
        fn = sum(1 for case in self.cases if case.expected_tension and not case.predicted_tension)
        tn = sum(1 for case in self.cases if not case.expected_tension and not case.predicted_tension)
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0
        specificity = tn / (tn + fp) if tn + fp else 1.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return {
            "case_count": len(self.cases),
            "external_sources": len({sid for case in self.cases for sid in case.report.get("source_ids", [])}),
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
            "kind_matches": sum(1 for case in self.cases if case.expected_tension and case.kind_match),
            "experiment_matches": sum(1 for case in self.cases if case.expected_tension and case.experiment_match),
            "correct_abstentions": sum(1 for case in self.cases if case.abstained_correctly),
            "label_firewall_verified": self.label_firewall_verified,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/independent-discovery-challenge/v1",
            "run_id": self.run_id,
            "created_at": self.created_at,
            "challenge_id": self.challenge_id,
            "corpus_hash": self.corpus_hash,
            "labels_hash": self.labels_hash,
            "source_registry_hash": self.source_registry_hash,
            "engine_version": self.engine_version,
            "label_firewall_verified": self.label_firewall_verified,
            "metadata": self.metadata,
            "summary": self.summary(),
            "cases": [case.to_dict() for case in self.cases],
        }
