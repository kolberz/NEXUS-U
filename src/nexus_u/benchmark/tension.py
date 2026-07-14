from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from typing import Any

from nexus_u.federation import (
    ActorRole,
    EvidenceSubmission,
    EvidenceVerdict,
    FederationActor,
    FederationLedger,
)
from nexus_u.security.signing import write_signed_envelope
from nexus_u.tension import (
    DiscoveryHypothesis,
    DiscriminatingExperiment,
    HypothesisKind,
    ObservedExperimentResult,
    TensionDiscoveryEngine,
    TensionKind,
)


@dataclass(slots=True)
class TensionBenchmarkCase:
    case_id: str
    tension_kind: str
    tension_detected: bool
    expected_experiment: str
    actual_experiment: str | None
    matched: bool
    static_baseline_experiment: str
    static_baseline_matched: bool
    tension_score_before: float
    tension_score_after: float
    tension_reduction: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TensionBenchmarkReport:
    started_at: float
    completed_at: float
    cases: list[TensionBenchmarkCase]

    def summary(self) -> dict[str, Any]:
        total = len(self.cases)
        detected = sum(item.tension_detected for item in self.cases)
        matches = sum(item.matched for item in self.cases)
        baseline = sum(item.static_baseline_matched for item in self.cases)
        reduced = sum(item.tension_reduction > 0 for item in self.cases)
        return {
            "case_count": total,
            "tensions_detected": detected,
            "detection_rate": round(detected / total, 6) if total else 0.0,
            "experiment_matches": matches,
            "experiment_match_rate": round(matches / total, 6) if total else 0.0,
            "static_baseline_matches": baseline,
            "static_baseline_rate": round(baseline / total, 6) if total else 0.0,
            "discovery_advantage": round((matches - baseline) / total, 6) if total else 0.0,
            "tension_reduced_cases": reduced,
            "mean_tension_reduction": round(sum(item.tension_reduction for item in self.cases) / total, 6) if total else 0.0,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/tension-discovery-benchmark/v1",
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": self.summary(),
            "cases": [item.to_dict() for item in self.cases],
        }


def _ledger(case_id: str, kind: TensionKind) -> tuple[FederationLedger, str]:
    ledger = FederationLedger()
    support = FederationActor("support", "lab-a", [ActorRole.REVIEWER], "support-key", 1.0)
    refute = FederationActor("refute", "lab-b", [ActorRole.VERIFIER], "refute-key", 1.0)
    ledger.register_actor(support, secret="support-secret")
    ledger.register_actor(refute, secret="refute-secret")
    obligation = f"discovery:{case_id}"
    metadata = {
        "tension_kind": kind.value,
        "statement": f"Independent evidence is incompatible for {case_id}",
    }
    ledger.submit(EvidenceSubmission(
        obligation_id=obligation,
        actor_id=support.actor_id,
        organization_id=support.organization_id,
        verdict=EvidenceVerdict.SUPPORTS,
        evidence_kind="benchmark",
        summary="Independent evidence supports the current explanation",
        evidence_digest=ledger.digest_evidence({"case": case_id, "side": "support"}),
        provenance_group=f"{case_id}-support",
        metadata=metadata,
    ))
    ledger.submit(EvidenceSubmission(
        obligation_id=obligation,
        actor_id=refute.actor_id,
        organization_id=refute.organization_id,
        verdict=EvidenceVerdict.REFUTES,
        evidence_kind="benchmark",
        summary="Independent evidence contradicts the current explanation",
        evidence_digest=ledger.digest_evidence({"case": case_id, "side": "refute"}),
        provenance_group=f"{case_id}-refute",
        metadata=metadata,
    ))
    return ledger, obligation


def _case_inputs(case_id: str, kind: TensionKind, h1_kind: HypothesisKind, h2_kind: HypothesisKind):
    ledger, obligation = _ledger(case_id, kind)
    h1 = DiscoveryHypothesis(
        tension_id="pending", hypothesis_id=f"{case_id}-h1",
        description=f"Minimal repair through {h1_kind.value}", kind=h1_kind,
        prior=0.5, complexity=1.0, predicted_resolution=0.8,
    )
    h2 = DiscoveryHypothesis(
        tension_id="pending", hypothesis_id=f"{case_id}-h2",
        description=f"Alternative explanation through {h2_kind.value}", kind=h2_kind,
        prior=0.5, complexity=2.0, predicted_resolution=0.8,
    )
    distractor = DiscriminatingExperiment(
        experiment_id=f"{case_id}-repeat",
        description="Repeat the same aggregate observation",
        outcomes=["a", "b"],
        likelihoods={h1.hypothesis_id: {"a": 0.6, "b": 0.4}, h2.hypothesis_id: {"a": 0.4, "b": 0.6}},
        cost=1.0,
    )
    discriminating = DiscriminatingExperiment(
        experiment_id=f"{case_id}-discriminate",
        description="Intervene on the variable that separates the competing explanations",
        outcomes=["a", "b"],
        likelihoods={h1.hypothesis_id: {"a": 0.95, "b": 0.05}, h2.hypothesis_id: {"a": 0.05, "b": 0.95}},
        cost=1.0,
    )
    expensive = DiscriminatingExperiment(
        experiment_id=f"{case_id}-expensive",
        description="Broad high-cost scan with similar discrimination",
        outcomes=["a", "b"],
        likelihoods={h1.hypothesis_id: {"a": 0.96, "b": 0.04}, h2.hypothesis_id: {"a": 0.04, "b": 0.96}},
        cost=4.0,
        risk=0.2,
    )
    return ledger, obligation, [h1, h2], [distractor, discriminating, expensive], discriminating.experiment_id


def run_tension_benchmark(
    *,
    output_dir: str | Path,
    signing_secret: str | None = None,
    key_id: str = "tension-discovery-local",
) -> tuple[TensionBenchmarkReport, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    engine = TensionDiscoveryEngine()
    definitions = [
        ("regime_split", TensionKind.SCOPE_CONFLICT, HypothesisKind.NARROW_SCOPE, HypothesisKind.MODEL_REVISION),
        ("calibration_anomaly", TensionKind.MODEL_DATA_MISMATCH, HypothesisKind.CALIBRATION_ERROR, HypothesisKind.MODEL_REVISION),
        ("hidden_dependency", TensionKind.CAUSAL_CONFLICT, HypothesisKind.HIDDEN_VARIABLE, HypothesisKind.NARROW_SCOPE),
        ("resource_transition", TensionKind.RESOURCE_CONFLICT, HypothesisKind.RESOURCE_REGIME, HypothesisKind.MODEL_REVISION),
        ("composition_failure", TensionKind.COMPOSITION_FAILURE, HypothesisKind.DEPENDENCY_CORRECTION, HypothesisKind.NARROW_SCOPE),
        ("mechanism_revision", TensionKind.CONTRADICTION, HypothesisKind.MODEL_REVISION, HypothesisKind.CALIBRATION_ERROR),
    ]
    cases: list[TensionBenchmarkCase] = []
    for case_id, kind, h1_kind, h2_kind in definitions:
        ledger, obligation, hypotheses, experiments, expected = _case_inputs(case_id, kind, h1_kind, h2_kind)
        observed = ObservedExperimentResult(expected, "a")
        report = engine.run(
            ledger, obligation, hypotheses=hypotheses, experiments=experiments, observed_result=observed
        )
        actual = report.recommendation.experiment_id if report.recommendation else None
        baseline = experiments[0].experiment_id
        cases.append(TensionBenchmarkCase(
            case_id=case_id,
            tension_kind=kind.value,
            tension_detected=bool(report.tensions),
            expected_experiment=expected,
            actual_experiment=actual,
            matched=actual == expected,
            static_baseline_experiment=baseline,
            static_baseline_matched=baseline == expected,
            tension_score_before=report.tension_score_before,
            tension_score_after=report.tension_score_after,
            tension_reduction=report.tension_reduction,
        ))
    report = TensionBenchmarkReport(started, time.time(), cases)
    path = output / "tension-benchmark.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    if signing_secret:
        write_signed_envelope(
            report.to_dict(), output / "tension-benchmark.signed.json", key_id=key_id, secret=signing_secret
        )
    return report, path
