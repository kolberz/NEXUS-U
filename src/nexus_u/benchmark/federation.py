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
    FederationDecisionStatus,
    FederationLedger,
    QuorumPolicy,
)
from nexus_u.security.signing import write_signed_envelope


@dataclass(slots=True)
class FederationBenchmarkCase:
    case_id: str
    expected: FederationDecisionStatus
    actual: FederationDecisionStatus
    matched: bool
    approved: bool
    organizations: int
    independent_groups: int
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FederationBenchmarkReport:
    started_at: float
    completed_at: float
    cases: list[FederationBenchmarkCase]

    def summary(self) -> dict[str, Any]:
        total = len(self.cases)
        matches = sum(case.matched for case in self.cases)
        return {
            "case_count": total,
            "expected_outcomes_matched": matches,
            "match_rate": round(matches / total, 6) if total else 0.0,
            "approved_cases": sum(case.approved for case in self.cases),
            "blocked_or_conflicted_cases": sum(not case.approved for case in self.cases),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/federated-evidence-benchmark/v1",
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": self.summary(),
            "cases": [case.to_dict() for case in self.cases],
        }


def _actor(actor_id: str, org: str, roles: list[ActorRole], weight: float = 1.0) -> FederationActor:
    return FederationActor(actor_id, org, roles, key_id=f"{actor_id}-key", trust_weight=weight)


def _submit(
    ledger: FederationLedger,
    actor: FederationActor,
    obligation: str,
    verdict: EvidenceVerdict,
    group: str,
    summary: str,
) -> None:
    ledger.submit(EvidenceSubmission(
        obligation_id=obligation,
        actor_id=actor.actor_id,
        organization_id=actor.organization_id,
        verdict=verdict,
        evidence_kind="benchmark",
        summary=summary,
        evidence_digest=ledger.digest_evidence({"summary": summary, "group": group}),
        provenance_group=group,
    ))


def _base_ledger() -> tuple[FederationLedger, dict[str, FederationActor]]:
    ledger = FederationLedger()
    actors = {
        "dev": _actor("dev", "engineering", [ActorRole.CONTRIBUTOR], 0.8),
        "review": _actor("review", "quality", [ActorRole.REVIEWER], 1.0),
        "verify": _actor("verify", "assurance", [ActorRole.VERIFIER], 1.2),
        "security": _actor("security", "security", [ActorRole.SECURITY], 1.3),
        "release": _actor("release", "operations", [ActorRole.RELEASE_MANAGER], 1.0),
    }
    for actor in actors.values():
        ledger.register_actor(actor, secret=f"secret-{actor.actor_id}")
    return ledger, actors


def run_federation_benchmark(
    *,
    output_dir: str | Path,
    signing_secret: str | None = None,
    key_id: str = "federated-evidence-local",
) -> tuple[FederationBenchmarkReport, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    cases: list[FederationBenchmarkCase] = []

    def run_case(case_id: str, expected: FederationDecisionStatus, setup) -> None:
        ledger, actors = _base_ledger()
        obligation, policy = setup(ledger, actors)
        decision = ledger.evaluate(obligation, policy)
        cases.append(FederationBenchmarkCase(
            case_id=case_id,
            expected=expected,
            actual=decision.status,
            matched=decision.status == expected,
            approved=decision.approved,
            organizations=len(decision.participating_organizations),
            independent_groups=len(decision.independent_evidence_groups),
            reasons=decision.reasons,
        ))

    def valid(ledger, actors):
        obligation = "release:complete"
        _submit(ledger, actors["review"], obligation, EvidenceVerdict.SUPPORTS, "tests", "Behavioral suite passed")
        _submit(ledger, actors["verify"], obligation, EvidenceVerdict.SUPPORTS, "formal", "Verifier accepted contract")
        policy = QuorumPolicy("valid", minimum_organizations=2, minimum_weight=2.0,
                              minimum_independent_evidence=2,
                              required_roles=[ActorRole.REVIEWER, ActorRole.VERIFIER])
        return obligation, policy

    def correlated(ledger, actors):
        obligation = "release:independence"
        _submit(ledger, actors["review"], obligation, EvidenceVerdict.SUPPORTS, "same-ci-run", "Review copied CI output")
        _submit(ledger, actors["verify"], obligation, EvidenceVerdict.SUPPORTS, "same-ci-run", "Verifier copied same CI output")
        policy = QuorumPolicy("independence", minimum_organizations=2, minimum_weight=2.0,
                              minimum_independent_evidence=2)
        return obligation, policy

    def conflict(ledger, actors):
        obligation = "release:no-conflict"
        _submit(ledger, actors["review"], obligation, EvidenceVerdict.SUPPORTS, "tests", "Tests passed")
        _submit(ledger, actors["verify"], obligation, EvidenceVerdict.REFUTES, "formal", "Contract violation found")
        policy = QuorumPolicy("conflict", minimum_organizations=1, minimum_weight=1.0,
                              minimum_independent_evidence=1)
        return obligation, policy

    def veto(ledger, actors):
        obligation = "release:security"
        _submit(ledger, actors["review"], obligation, EvidenceVerdict.SUPPORTS, "tests", "Tests passed")
        _submit(ledger, actors["security"], obligation, EvidenceVerdict.REFUTES, "security-scan", "Critical vulnerability")
        policy = QuorumPolicy("veto", minimum_organizations=1, minimum_weight=1.0,
                              minimum_independent_evidence=1,
                              require_no_conflicts=False, veto_roles=[ActorRole.SECURITY])
        return obligation, policy

    def dependency(ledger, actors):
        obligation = "release:cross-repo"
        _submit(ledger, actors["review"], obligation, EvidenceVerdict.SUPPORTS, "tests", "Consumer tests passed")
        _submit(ledger, actors["verify"], obligation, EvidenceVerdict.SUPPORTS, "formal", "Consumer contract passed")
        policy = QuorumPolicy("dependency", minimum_organizations=2, minimum_weight=2.0,
                              minimum_independent_evidence=2,
                              required_dependencies=["repo:shared-schema@abc123"])
        return obligation, policy

    def human_authority(ledger, actors):
        obligation = "release:constitutional-change"
        _submit(ledger, actors["review"], obligation, EvidenceVerdict.SUPPORTS, "review", "Change reviewed")
        _submit(ledger, actors["verify"], obligation, EvidenceVerdict.SUPPORTS, "formal", "Mechanism verified")
        policy = QuorumPolicy("authority", minimum_organizations=2, minimum_weight=2.0,
                              minimum_independent_evidence=2,
                              required_roles=[ActorRole.OWNER])
        return obligation, policy

    run_case("independent_quorum", FederationDecisionStatus.APPROVED, valid)
    run_case("correlated_evidence", FederationDecisionStatus.INSUFFICIENT_QUORUM, correlated)
    run_case("conflicting_evidence", FederationDecisionStatus.CONFLICT, conflict)
    run_case("security_veto", FederationDecisionStatus.BLOCKED, veto)
    run_case("missing_cross_repo_dependency", FederationDecisionStatus.MISSING_DEPENDENCY, dependency)
    run_case("missing_human_authority", FederationDecisionStatus.INSUFFICIENT_QUORUM, human_authority)

    report = FederationBenchmarkReport(started, time.time(), cases)
    path = output / "federation-benchmark.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    if signing_secret:
        write_signed_envelope(report.to_dict(), output / "federation-benchmark.signed.json",
                              key_id=key_id, secret=signing_secret)
    return report, path
