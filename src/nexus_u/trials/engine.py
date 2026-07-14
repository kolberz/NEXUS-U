from __future__ import annotations

from nexus_u import __version__
from nexus_u.federation import ActorRole, EvidenceSubmission, EvidenceVerdict, FederationActor, FederationLedger
from nexus_u.tension import TensionDiscoveryEngine

from .io import corpus_digest
from .models import DiscoveryTrialReport, TrialCase, TrialCaseResult, TrialExpectation


class DiscoveryTrialRunner:
    """Blind trial runner for heterogeneous, provenance-bearing claim corpora.

    Expected labels are used only after inference to score the report. The
    discovery engine receives claims, source identity, provenance, and scope,
    but not the expected tension label or expected experiment.
    """

    def __init__(self) -> None:
        self.engine = TensionDiscoveryEngine()

    @staticmethod
    def _ledger(case: TrialCase) -> FederationLedger:
        ledger = FederationLedger()
        actor_ids: set[str] = set()
        for claim in case.claims:
            actor_id = f"actor:{claim.source_id}"
            if actor_id not in actor_ids:
                ledger.register_actor(FederationActor(
                    actor_id=actor_id,
                    organization_id=claim.organization_id,
                    roles=[ActorRole.CONTRIBUTOR],
                    key_id=f"{actor_id}:key",
                    trust_weight=claim.trust_weight,
                    authority_scopes=[claim.scope, "*"],
                    metadata={"source_title": claim.source_title},
                ), secret=f"trial:{claim.source_id}:secret")
                actor_ids.add(actor_id)
            verdict = EvidenceVerdict(claim.verdict)
            ledger.submit(EvidenceSubmission(
                obligation_id=case.case_id,
                actor_id=actor_id,
                organization_id=claim.organization_id,
                verdict=verdict,
                evidence_kind=claim.evidence_kind,
                summary=claim.statement,
                evidence_digest=ledger.digest_evidence({
                    "claim_id": claim.claim_id,
                    "statement": claim.statement,
                    "source": claim.source_id,
                }),
                provenance_group=claim.provenance_group,
                scope=claim.scope,
                metadata={
                    "statement": case.title,
                    "tension_kind": claim.tension_kind.value,
                    "claim_id": claim.claim_id,
                    "source_id": claim.source_id,
                    **claim.metadata,
                },
            ))
        return ledger

    def run_case(self, case: TrialCase) -> TrialCaseResult:
        report = self.engine.run(self._ledger(case), case.case_id)
        predicted_tension = bool(report.tensions)
        predicted_kind = report.tensions[0].kind.value if report.tensions else None
        expected_kind = case.expected_kind.value if case.expected_kind else None
        kind_match = (
            case.expectation == TrialExpectation.NO_TENSION and predicted_kind is None
        ) or (
            case.expectation == TrialExpectation.TENSION and predicted_kind == expected_kind
        )
        recommendation = report.recommendation
        experiment_description = None
        experiment_match = case.expectation == TrialExpectation.NO_TENSION and recommendation is None
        if recommendation:
            experiment = next(
                (item for item in report.experiments if item.experiment_id == recommendation.experiment_id),
                None,
            )
            experiment_description = experiment.description if experiment else None
            if case.expected_experiment_terms:
                lowered = (experiment_description or "").lower()
                experiment_match = any(term in lowered for term in case.expected_experiment_terms)
            else:
                experiment_match = True
        return TrialCaseResult(
            case_id=case.case_id,
            expected=case.expectation,
            predicted_tension=predicted_tension,
            expected_kind=expected_kind,
            predicted_kind=predicted_kind,
            kind_match=kind_match,
            experiment_match=experiment_match,
            false_discovery=case.expectation == TrialExpectation.NO_TENSION and predicted_tension,
            missed_tension=case.expectation == TrialExpectation.TENSION and not predicted_tension,
            abstained_correctly=case.expectation == TrialExpectation.NO_TENSION and not predicted_tension,
            tension_score=report.tension_score_before,
            recommended_experiment=experiment_description,
            source_count=len(case.claims),
            provenance_groups=len({claim.provenance_group for claim in case.claims}),
            report=report.to_dict(),
        )

    def run_suite(self, suite_id: str, cases: list[TrialCase], metadata: dict | None = None) -> DiscoveryTrialReport:
        return DiscoveryTrialReport(
            suite_id=suite_id,
            cases=[self.run_case(case) for case in cases],
            corpus_hash=corpus_digest(cases),
            engine_version=__version__,
            metadata=metadata or {},
        )
