from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus_u.federation import (
    ActorRole,
    CrossRepositoryObligation,
    EvidenceSubmission,
    EvidenceVerdict,
    FederationActor,
    FederationDecisionStatus,
    FederationError,
    FederationLedger,
    QuorumPolicy,
    merge_graphs,
)
from nexus_u.storage.sqlite import ControlStore


def actor(actor_id: str, org: str, roles: list[ActorRole], weight: float = 1.0) -> FederationActor:
    return FederationActor(actor_id, org, roles, key_id=f"{actor_id}-key", trust_weight=weight)


def submit(ledger: FederationLedger, actor_value: FederationActor, obligation: str,
           verdict: EvidenceVerdict, group: str) -> EvidenceSubmission:
    return ledger.submit(EvidenceSubmission(
        obligation_id=obligation,
        actor_id=actor_value.actor_id,
        organization_id=actor_value.organization_id,
        verdict=verdict,
        evidence_kind="test",
        summary=f"{verdict.value} from {actor_value.actor_id}",
        evidence_digest=ledger.digest_evidence({"actor": actor_value.actor_id, "group": group}),
        provenance_group=group,
    ))


def setup_ledger():
    ledger = FederationLedger()
    review = actor("review", "quality", [ActorRole.REVIEWER], 1.0)
    verify = actor("verify", "assurance", [ActorRole.VERIFIER], 1.2)
    security = actor("security", "security", [ActorRole.SECURITY], 1.3)
    for item in (review, verify, security):
        ledger.register_actor(item, secret=f"secret-{item.actor_id}")
    return ledger, review, verify, security


def test_independent_quorum_approves():
    ledger, review, verify, _ = setup_ledger()
    submit(ledger, review, "o1", EvidenceVerdict.SUPPORTS, "tests")
    submit(ledger, verify, "o1", EvidenceVerdict.SUPPORTS, "formal")
    decision = ledger.evaluate("o1", QuorumPolicy(
        "p1", required_roles=[ActorRole.REVIEWER, ActorRole.VERIFIER]
    ))
    assert decision.status == FederationDecisionStatus.APPROVED
    assert decision.total_weight == pytest.approx(2.2)


def test_correlated_evidence_does_not_fake_independence():
    ledger, review, verify, _ = setup_ledger()
    submit(ledger, review, "o1", EvidenceVerdict.SUPPORTS, "same-run")
    submit(ledger, verify, "o1", EvidenceVerdict.SUPPORTS, "same-run")
    decision = ledger.evaluate("o1", QuorumPolicy("p1", minimum_independent_evidence=2))
    assert decision.status == FederationDecisionStatus.INSUFFICIENT_QUORUM
    assert len(decision.independent_evidence_groups) == 1


def test_conflict_and_security_veto_block():
    ledger, review, verify, security = setup_ledger()
    submit(ledger, review, "conflict", EvidenceVerdict.SUPPORTS, "tests")
    submit(ledger, verify, "conflict", EvidenceVerdict.REFUTES, "formal")
    decision = ledger.evaluate("conflict", QuorumPolicy("conflict", minimum_organizations=1,
                                                        minimum_weight=1, minimum_independent_evidence=1))
    assert decision.status == FederationDecisionStatus.CONFLICT

    submit(ledger, review, "veto", EvidenceVerdict.SUPPORTS, "tests-veto")
    submit(ledger, security, "veto", EvidenceVerdict.REFUTES, "security")
    decision = ledger.evaluate("veto", QuorumPolicy("veto", minimum_organizations=1,
                                                     minimum_weight=1, minimum_independent_evidence=1,
                                                     require_no_conflicts=False))
    assert decision.status == FederationDecisionStatus.BLOCKED


def test_tampered_submission_is_rejected():
    ledger, review, _, _ = setup_ledger()
    item = submit(ledger, review, "o1", EvidenceVerdict.SUPPORTS, "tests")
    item.summary = "tampered"
    ok, errors = ledger.verify_submission(item)
    assert not ok
    assert "Signature mismatch" in errors
    with pytest.raises(FederationError):
        ledger.submit(item)


def test_missing_cross_repo_dependency_blocks():
    ledger, review, verify, _ = setup_ledger()
    submit(ledger, review, "o1", EvidenceVerdict.SUPPORTS, "tests")
    submit(ledger, verify, "o1", EvidenceVerdict.SUPPORTS, "formal")
    policy = QuorumPolicy("dependency", required_dependencies=["repo:schema@abc"])
    decision = ledger.evaluate("o1", policy)
    assert decision.status == FederationDecisionStatus.MISSING_DEPENDENCY
    ledger.mark_dependency("repo:schema@abc")
    assert ledger.evaluate("o1", policy).approved


def test_graph_merge_namespaces_and_rejects_missing_links():
    graph_a = {"nodes": [{"node_id": "a", "metadata": {}}], "edges": []}
    graph_b = {"nodes": [{"node_id": "b", "metadata": {}}], "edges": []}
    good = merge_graphs({"repo-a": graph_a, "repo-b": graph_b}, [
        CrossRepositoryObligation("repo-a", "a", "repo-b", "b")
    ])
    assert good["federation_valid"]
    assert {node["node_id"] for node in good["nodes"]} == {"repo-a:a", "repo-b:b"}
    bad = merge_graphs({"repo-a": graph_a}, [
        CrossRepositoryObligation("repo-a", "a", "repo-b", "b")
    ])
    assert not bad["federation_valid"]


def test_control_store_persists_federation_records(tmp_path: Path):
    ledger, review, verify, _ = setup_ledger()
    submit(ledger, review, "o1", EvidenceVerdict.SUPPORTS, "tests")
    submit(ledger, verify, "o1", EvidenceVerdict.SUPPORTS, "formal")
    decision = ledger.evaluate("o1", QuorumPolicy("p1"))
    store = ControlStore(tmp_path / "control.db")
    for item in ledger.evidence_for("o1"):
        store.record_federation_evidence(item)
    store.record_federation_decision(decision)
    assert len(store.list_federation_evidence("o1")) == 2
    decisions = store.list_federation_decisions("o1")
    assert len(decisions) == 1
    assert decisions[0]["approved"] is True
