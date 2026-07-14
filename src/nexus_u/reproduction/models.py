from __future__ import annotations

from dataclasses import asdict, dataclass, field
import time
from typing import Any
import uuid


@dataclass(slots=True)
class EvaluatorIdentity:
    evaluator_id: str
    key_id: str
    organization: str
    independence_scope: str = "process_isolated_not_external"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Preregistration:
    protocol_id: str
    title: str
    engine_version: str
    corpus_hash: str
    labels_hash: str
    source_registry_hash: str
    seed: str
    sample_size: int
    selection_algorithm: str
    selected_case_ids: list[str]
    evaluators: list[EvaluatorIdentity]
    evaluator_quorum: int
    primary_metrics: list[str]
    success_criteria: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    protocol_hash: str = ""

    def hash_payload(self) -> dict[str, Any]:
        raw = asdict(self)
        raw.pop("protocol_hash", None)
        return raw

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["schema"] = "https://nexus-u.dev/preregistered-reproduction/protocol/v1"
        return raw


@dataclass(slots=True)
class EvaluatorResult:
    evaluator_id: str
    key_id: str
    organization: str
    independence_scope: str
    protocol_hash: str
    corpus_hash: str
    labels_hash: str
    selected_case_ids: list[str]
    sealed_predictions_hash: str
    inference_process_id: int
    inference_engine_version: str
    metrics: dict[str, Any]
    predictions: list[dict[str, Any]]
    label_firewall_verified: bool
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["schema"] = "https://nexus-u.dev/preregistered-reproduction/evaluator-result/v1"
        return raw


@dataclass(slots=True)
class ReproductionReport:
    protocol: Preregistration
    evaluator_results: list[dict[str, Any]]
    valid_signatures: int
    protocol_matches: int
    distinct_key_ids: int
    exact_prediction_agreement: bool
    exact_metric_agreement: bool
    deterministic_sampling_verified: bool
    label_firewall_verified: bool
    tamper_detection_verified: bool
    process_isolation_verified: bool
    replay_bundle_hash: str
    external_independence_claimed: bool = False
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def summary(self) -> dict[str, Any]:
        count = len(self.evaluator_results)
        quorum = self.protocol.evaluator_quorum
        reproduced = (
            count >= quorum
            and self.valid_signatures >= quorum
            and self.protocol_matches >= quorum
            and self.distinct_key_ids >= quorum
            and self.exact_prediction_agreement
            and self.exact_metric_agreement
            and self.deterministic_sampling_verified
            and self.label_firewall_verified
            and self.tamper_detection_verified
            and self.process_isolation_verified
        )
        metrics = self.evaluator_results[0]["payload"]["metrics"] if self.evaluator_results else {}
        return {
            "status": "PROCESS_REPRODUCED" if reproduced else "REPRODUCTION_FAILED",
            "evaluator_count": count,
            "evaluator_quorum": quorum,
            "valid_signatures": self.valid_signatures,
            "protocol_matches": self.protocol_matches,
            "distinct_key_ids": self.distinct_key_ids,
            "exact_prediction_agreement": self.exact_prediction_agreement,
            "exact_metric_agreement": self.exact_metric_agreement,
            "deterministic_sampling_verified": self.deterministic_sampling_verified,
            "label_firewall_verified": self.label_firewall_verified,
            "tamper_detection_verified": self.tamper_detection_verified,
            "process_isolation_verified": self.process_isolation_verified,
            "external_independence_claimed": self.external_independence_claimed,
            "sample_size": len(self.protocol.selected_case_ids),
            "metrics": metrics,
            "reproduced": reproduced,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/preregistered-reproduction/report/v1",
            "run_id": self.run_id,
            "created_at": self.created_at,
            "protocol": self.protocol.to_dict(),
            "summary": self.summary(),
            "evaluator_results": self.evaluator_results,
            "replay_bundle_hash": self.replay_bundle_hash,
        }
