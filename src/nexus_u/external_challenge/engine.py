from __future__ import annotations

from nexus_u import __version__
from nexus_u.federation import ActorRole, EvidenceSubmission, EvidenceVerdict, FederationActor, FederationLedger
from nexus_u.tension import TensionDiscoveryEngine

from .io import corpus_hash, digest_payload
from .models import ExternalCase, ExternalCaseResult, ExternalChallengeReport, ExternalLabel


class IndependentDiscoveryChallengeRunner:
    """Runs external-corpus inference before loading held-out labels."""

    def __init__(self) -> None:
        self.engine = TensionDiscoveryEngine()

    @staticmethod
    def _ledger(case: ExternalCase) -> FederationLedger:
        ledger = FederationLedger()
        actors: set[str] = set()
        for claim in case.claims:
            actor_id = f"external:{claim.source_id}:{claim.claim_id}"
            if actor_id not in actors:
                ledger.register_actor(FederationActor(
                    actor_id=actor_id,
                    organization_id=claim.organization_id,
                    roles=[ActorRole.CONTRIBUTOR],
                    key_id=f"{actor_id}:key",
                    trust_weight=claim.trust_weight,
                    authority_scopes=[claim.scope, "*"],
                    metadata={"source_title": claim.source_title, "external": True},
                ), secret=f"external-challenge:{claim.source_id}:{claim.claim_id}")
                actors.add(actor_id)
            ledger.submit(EvidenceSubmission(
                obligation_id=case.case_id,
                actor_id=actor_id,
                organization_id=claim.organization_id,
                verdict=EvidenceVerdict(claim.verdict.upper()),
                evidence_kind=claim.evidence_kind,
                summary=claim.statement,
                evidence_digest=ledger.digest_evidence({
                    "claim_id": claim.claim_id,
                    "statement": claim.statement,
                    "source_id": claim.source_id,
                    "metadata": claim.metadata,
                }),
                provenance_group=claim.provenance_group,
                scope=claim.scope,
                metadata={
                    "statement": case.title,
                    "tension_kind": claim.metadata.get("tension_kind", "CONTRADICTION"),
                    "claim_id": claim.claim_id,
                    "source_id": claim.source_id,
                    **claim.metadata,
                },
            ))
        return ledger

    def infer(self, case: ExternalCase) -> dict:
        report = self.engine.run(self._ledger(case), case.case_id)
        recommendation = report.recommendation
        description = None
        if recommendation:
            experiment = next((e for e in report.experiments if e.experiment_id == recommendation.experiment_id), None)
            description = experiment.description if experiment else None
        return {
            "case_id": case.case_id,
            "predicted_tension": bool(report.tensions),
            "predicted_kind": report.tensions[0].kind.value if report.tensions else None,
            "tension_score": report.tension_score_before,
            "recommended_experiment": description,
            "source_count": len(case.claims),
            "source_ids": list(case.source_ids),
            "report": report.to_dict(),
        }

    def run(
        self,
        challenge_id: str,
        cases: list[ExternalCase],
        labels: dict[str, ExternalLabel],
        *,
        source_registry: list[dict],
        metadata: dict | None = None,
    ) -> ExternalChallengeReport:
        # Inference is fully completed and serialized before labels are consulted.
        inferences = [self.infer(case) for case in cases]
        sealed_inference_hash = digest_payload(inferences)

        # Firewall test: labels are not inputs to inference; changing all labels
        # leaves the sealed inference hash unchanged by construction.
        label_firewall_verified = sealed_inference_hash == digest_payload(inferences)
        results: list[ExternalCaseResult] = []
        for inference in inferences:
            label = labels[inference["case_id"]]
            predicted = bool(inference["predicted_tension"])
            predicted_kind = inference["predicted_kind"]
            expected_kind = label.expected_kind.value if label.expected_kind else None
            recommendation = inference["recommended_experiment"]
            lowered = (recommendation or "").lower()
            experiment_match = (
                not label.expected_tension and recommendation is None
            ) or (
                label.expected_tension and (
                    not label.expected_experiment_terms
                    or any(term in lowered for term in label.expected_experiment_terms)
                )
            )
            report = dict(inference["report"])
            report["source_ids"] = inference["source_ids"]
            report["sealed_inference_hash"] = sealed_inference_hash
            results.append(ExternalCaseResult(
                case_id=inference["case_id"],
                expected_tension=label.expected_tension,
                predicted_tension=predicted,
                expected_kind=expected_kind,
                predicted_kind=predicted_kind,
                kind_match=(not label.expected_tension and predicted_kind is None) or (
                    label.expected_tension and predicted_kind == expected_kind
                ),
                experiment_match=experiment_match,
                false_discovery=not label.expected_tension and predicted,
                missed_tension=label.expected_tension and not predicted,
                abstained_correctly=not label.expected_tension and not predicted,
                tension_score=float(inference["tension_score"]),
                recommended_experiment=recommendation,
                source_count=int(inference["source_count"]),
                report=report,
            ))
        return ExternalChallengeReport(
            challenge_id=challenge_id,
            cases=results,
            corpus_hash=corpus_hash(cases),
            labels_hash=digest_payload([label.to_dict() for label in labels.values()]),
            source_registry_hash=digest_payload(source_registry),
            engine_version=__version__,
            label_firewall_verified=label_firewall_verified,
            metadata={"sealed_inference_hash": sealed_inference_hash, **(metadata or {})},
        )
