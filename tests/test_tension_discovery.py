from __future__ import annotations

from nexus_u.federation import ActorRole, EvidenceSubmission, EvidenceVerdict, FederationActor, FederationLedger
from nexus_u.tension import (
    DiscoveryHypothesis,
    DiscoveryStatus,
    DiscriminatingExperiment,
    HypothesisKind,
    ObservedExperimentResult,
    TensionDiscoveryEngine,
    TensionKind,
)


def make_ledger(*, same_group: bool = False) -> tuple[FederationLedger, str]:
    ledger = FederationLedger()
    a = FederationActor("a", "org-a", [ActorRole.REVIEWER], "a-key", 1.0)
    b = FederationActor("b", "org-b", [ActorRole.VERIFIER], "b-key", 1.0)
    ledger.register_actor(a, secret="a-secret")
    ledger.register_actor(b, secret="b-secret")
    obligation = "claim:x"
    meta = {"tension_kind": TensionKind.MODEL_DATA_MISMATCH.value, "statement": "Model and observation disagree"}
    ledger.submit(EvidenceSubmission(
        obligation, "a", "org-a", EvidenceVerdict.SUPPORTS, "test", "supports", ledger.digest_evidence("a"),
        "shared" if same_group else "group-a", metadata=meta,
    ))
    ledger.submit(EvidenceSubmission(
        obligation, "b", "org-b", EvidenceVerdict.REFUTES, "test", "refutes", ledger.digest_evidence("b"),
        "shared" if same_group else "group-b", metadata=meta,
    ))
    return ledger, obligation


def test_detects_independent_tension_and_generates_hypotheses() -> None:
    ledger, obligation = make_ledger()
    report = TensionDiscoveryEngine().run(ledger, obligation)
    assert report.status == DiscoveryStatus.EXPERIMENT_RECOMMENDED
    assert report.tension_score_before == 1.0
    assert len(report.hypotheses) >= 3
    assert report.recommendation is not None


def test_correlated_provenance_does_not_count_as_full_independence() -> None:
    ledger, obligation = make_ledger(same_group=True)
    report = TensionDiscoveryEngine().run(ledger, obligation)
    assert report.tensions
    assert report.tension_score_before == 0.5


def test_observed_discriminating_result_reduces_tension() -> None:
    ledger, obligation = make_ledger()
    h1 = DiscoveryHypothesis("pending", "scope", HypothesisKind.NARROW_SCOPE, prior=0.5, hypothesis_id="h1")
    h2 = DiscoveryHypothesis("pending", "model", HypothesisKind.MODEL_REVISION, prior=0.5, hypothesis_id="h2")
    experiment = DiscriminatingExperiment(
        "scope test", ["scope", "model"],
        {"h1": {"scope": 0.95, "model": 0.05}, "h2": {"scope": 0.05, "model": 0.95}},
        experiment_id="e1",
    )
    report = TensionDiscoveryEngine().run(
        ledger, obligation, hypotheses=[h1, h2], experiments=[experiment],
        observed_result=ObservedExperimentResult("e1", "scope"),
    )
    assert report.status == DiscoveryStatus.TENSION_REDUCED
    assert report.tension_reduction > 0.5
    assert report.posterior_probabilities["h1"] > 0.9


def test_no_conflict_returns_no_tension() -> None:
    ledger = FederationLedger()
    actor = FederationActor("a", "org-a", [ActorRole.REVIEWER], "a-key")
    ledger.register_actor(actor, secret="secret")
    ledger.submit(EvidenceSubmission(
        "claim:y", "a", "org-a", EvidenceVerdict.SUPPORTS, "test", "supports",
        ledger.digest_evidence("a"), "group-a",
    ))
    report = TensionDiscoveryEngine().run(ledger, "claim:y")
    assert report.status == DiscoveryStatus.NO_TENSION
    assert report.tensions == []


def test_store_persists_tension_report(tmp_path) -> None:
    from nexus_u.storage.sqlite import ControlStore
    ledger, obligation = make_ledger()
    report = TensionDiscoveryEngine().run(ledger, obligation)
    store = ControlStore(tmp_path / "control.db")
    store.record_tension_discovery(report)
    loaded = store.get_tension_discovery(report.run_id)
    assert loaded is not None
    assert loaded["payload"]["obligation_id"] == obligation
    assert store.list_tension_discoveries(obligation)[0]["run_id"] == report.run_id
