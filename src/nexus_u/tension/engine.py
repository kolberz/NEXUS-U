from __future__ import annotations

import math
from typing import Iterable

from nexus_u.federation import EvidenceSubmission, EvidenceVerdict, FederationLedger

from .models import (
    DiscoveryHypothesis,
    DiscoveryStatus,
    DiscriminatingExperiment,
    ExperimentRecommendation,
    HypothesisKind,
    ObservedExperimentResult,
    Tension,
    TensionDiscoveryReport,
    TensionKind,
)


def _normalize(values: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, value) for value in values.values())
    if total <= 0:
        count = max(1, len(values))
        return {key: 1.0 / count for key in values}
    return {key: max(0.0, value) / total for key, value in values.items()}


def _entropy(probabilities: dict[str, float]) -> float:
    return -sum(value * math.log2(value) for value in probabilities.values() if value > 0)


class TensionDetector:
    def detect(self, ledger: FederationLedger, obligation_id: str) -> list[Tension]:
        submissions = ledger.evidence_for(obligation_id)
        valid: list[EvidenceSubmission] = []
        for item in submissions:
            ok, _ = ledger.verify_submission(item)
            if ok:
                valid.append(item)
        if not valid:
            return []

        support_groups: dict[str, tuple[float, EvidenceSubmission]] = {}
        refute_groups: dict[str, tuple[float, EvidenceSubmission]] = {}
        inconclusive = 0
        for item in valid:
            actor = ledger.actors[item.actor_id]
            target = support_groups if item.verdict == EvidenceVerdict.SUPPORTS else refute_groups
            if item.verdict == EvidenceVerdict.INCONCLUSIVE:
                inconclusive += 1
                continue
            current = target.get(item.provenance_group)
            if current is None or actor.trust_weight > current[0]:
                target[item.provenance_group] = (actor.trust_weight, item)

        support_weight = sum(value[0] for value in support_groups.values())
        refute_weight = sum(value[0] for value in refute_groups.values())
        if support_weight <= 0 or refute_weight <= 0:
            return []

        total = support_weight + refute_weight
        balance = 2.0 * min(support_weight, refute_weight) / total
        independent_groups = set(support_groups).union(refute_groups)
        independence = min(1.0, len(independent_groups) / 2.0)
        strength = min(1.0, total / 2.0)
        score = round(balance * independence * strength, 6)
        metadata = {}
        for item in valid:
            metadata.update(item.metadata)
        kind_raw = str(metadata.get("tension_kind", TensionKind.CONTRADICTION.value))
        try:
            kind = TensionKind(kind_raw)
        except ValueError:
            kind = TensionKind.CONTRADICTION
        statement = str(metadata.get("statement", f"Independent evidence conflicts on {obligation_id}"))
        organizations = sorted({item.organization_id for item in valid})
        return [Tension(
            obligation_id=obligation_id,
            statement=statement,
            kind=kind,
            score=score,
            support_weight=round(support_weight, 6),
            refute_weight=round(refute_weight, 6),
            supporting_evidence=[item.submission_id for _, item in support_groups.values()],
            refuting_evidence=[item.submission_id for _, item in refute_groups.values()],
            organizations=organizations,
            provenance_groups=sorted(independent_groups),
            metadata={"inconclusive_count": inconclusive, **metadata},
        )]


class MinimalRepairGenerator:
    def generate(self, tension: Tension) -> list[DiscoveryHypothesis]:
        common = {"tension_score": tension.score, "tension_kind": tension.kind.value}
        if tension.kind == TensionKind.RESOURCE_CONFLICT:
            templates = [
                (HypothesisKind.RESOURCE_REGIME, "The result changes across resource or scale regimes.", 1.0, 0.75),
                (HypothesisKind.CALIBRATION_ERROR, "One resource measurement or cost model is miscalibrated.", 1.5, 0.6),
                (HypothesisKind.MODEL_REVISION, "The current resource model omits a dominant cost channel.", 2.5, 0.8),
            ]
        elif tension.kind in {TensionKind.COMPOSITION_FAILURE, TensionKind.CAUSAL_CONFLICT}:
            templates = [
                (HypothesisKind.DEPENDENCY_CORRECTION, "An unmodeled dependency or causal path links the conflicting components.", 1.5, 0.85),
                (HypothesisKind.NARROW_SCOPE, "The obligations are compatible only in a narrower operating regime.", 1.0, 0.65),
                (HypothesisKind.MODEL_REVISION, "The composition or causal model is structurally incomplete.", 2.5, 0.8),
            ]
        else:
            templates = [
                (HypothesisKind.NARROW_SCOPE, "The claim is valid only under a narrower boundary condition or regime.", 1.0, 0.7),
                (HypothesisKind.CALIBRATION_ERROR, "One evidence stream contains calibration, measurement, or labeling error.", 1.5, 0.6),
                (HypothesisKind.HIDDEN_VARIABLE, "A latent variable separates the apparently conflicting observations.", 2.0, 0.85),
                (HypothesisKind.MODEL_REVISION, "The current explanatory model is incomplete and requires a new mechanism.", 3.0, 0.9),
            ]
        prior = 1.0 / len(templates)
        hypotheses = [DiscoveryHypothesis(
            tension_id=tension.tension_id,
            description=description,
            kind=kind,
            prior=prior,
            complexity=complexity,
            predicted_resolution=resolution,
            new_obligations=[f"Test {kind.value.lower()} explanation"],
            metadata=common,
        ) for kind, description, complexity, resolution in templates]
        return sorted(hypotheses, key=lambda item: item.discovery_value, reverse=True)


class ExperimentDesigner:
    def expected_information_gain(
        self,
        hypotheses: list[DiscoveryHypothesis],
        experiment: DiscriminatingExperiment,
    ) -> tuple[float, dict[str, float]]:
        priors = _normalize({item.hypothesis_id: item.prior for item in hypotheses})
        prior_entropy = _entropy(priors)
        outcome_probs: dict[str, float] = {}
        expected_posterior_entropy = 0.0
        for outcome in experiment.outcomes:
            probability = sum(
                priors[hypothesis.hypothesis_id]
                * float(experiment.likelihoods.get(hypothesis.hypothesis_id, {}).get(outcome, 0.0))
                for hypothesis in hypotheses
            )
            outcome_probs[outcome] = probability
            if probability <= 0:
                continue
            posterior = _normalize({
                hypothesis.hypothesis_id:
                    priors[hypothesis.hypothesis_id]
                    * float(experiment.likelihoods.get(hypothesis.hypothesis_id, {}).get(outcome, 0.0))
                for hypothesis in hypotheses
            })
            expected_posterior_entropy += probability * _entropy(posterior)
        return max(0.0, prior_entropy - expected_posterior_entropy), _normalize(outcome_probs)

    def recommend(
        self,
        hypotheses: list[DiscoveryHypothesis],
        experiments: list[DiscriminatingExperiment],
    ) -> ExperimentRecommendation | None:
        best: ExperimentRecommendation | None = None
        for experiment in experiments:
            information_gain, outcomes = self.expected_information_gain(hypotheses, experiment)
            utility = information_gain / max(0.001, experiment.cost * (1.0 + experiment.risk))
            recommendation = ExperimentRecommendation(
                experiment_id=experiment.experiment_id,
                expected_information_gain=round(information_gain, 6),
                utility=round(utility, 6),
                expected_outcome_probabilities={key: round(value, 6) for key, value in outcomes.items()},
                rationale=[
                    "Maximizes expected reduction in hypothesis uncertainty",
                    "Penalizes experiment cost and declared risk",
                ],
            )
            if best is None or recommendation.utility > best.utility:
                best = recommendation
        return best

    def posterior(
        self,
        hypotheses: list[DiscoveryHypothesis],
        experiment: DiscriminatingExperiment,
        outcome: str,
    ) -> dict[str, float]:
        if outcome not in experiment.outcomes:
            raise ValueError(f"Unknown experiment outcome: {outcome}")
        priors = _normalize({item.hypothesis_id: item.prior for item in hypotheses})
        return _normalize({
            hypothesis.hypothesis_id:
                priors[hypothesis.hypothesis_id]
                * float(experiment.likelihoods.get(hypothesis.hypothesis_id, {}).get(outcome, 0.0))
            for hypothesis in hypotheses
        })

    def default_experiments(self, hypotheses: list[DiscoveryHypothesis]) -> list[DiscriminatingExperiment]:
        if not hypotheses:
            return []
        ids = [item.hypothesis_id for item in hypotheses]
        outcomes = ["supports_scope_split", "supports_measurement_error", "supports_new_mechanism"]
        experiments: list[DiscriminatingExperiment] = []
        for name, favored_kind, cost in [
            ("Stratified replication across regimes", HypothesisKind.NARROW_SCOPE, 1.0),
            ("Independent recalibration and blinded replication", HypothesisKind.CALIBRATION_ERROR, 1.2),
            ("Targeted intervention on the suspected latent dependency", HypothesisKind.HIDDEN_VARIABLE, 1.5),
        ]:
            likelihoods: dict[str, dict[str, float]] = {}
            for hypothesis in hypotheses:
                favored = hypothesis.kind == favored_kind or (
                    favored_kind == HypothesisKind.HIDDEN_VARIABLE
                    and hypothesis.kind in {HypothesisKind.DEPENDENCY_CORRECTION, HypothesisKind.MODEL_REVISION}
                )
                target_index = (
                    0 if favored_kind == HypothesisKind.NARROW_SCOPE
                    else 1 if favored_kind == HypothesisKind.CALIBRATION_ERROR
                    else 2
                )
                if favored:
                    probabilities = [0.125, 0.125, 0.125]
                    probabilities[target_index] = 0.75
                else:
                    probabilities = [0.4, 0.4, 0.4]
                    probabilities[target_index] = 0.2
                likelihoods[hypothesis.hypothesis_id] = {
                    outcome: probabilities[index] for index, outcome in enumerate(outcomes)
                }
            experiments.append(DiscriminatingExperiment(
                description=name,
                outcomes=outcomes,
                likelihoods=likelihoods,
                cost=cost,
                risk=0.05,
                metadata={"default_generated": True, "hypothesis_ids": ids},
            ))
        return experiments


class TensionDiscoveryEngine:
    def __init__(self) -> None:
        self.detector = TensionDetector()
        self.generator = MinimalRepairGenerator()
        self.designer = ExperimentDesigner()

    def run(
        self,
        ledger: FederationLedger,
        obligation_id: str,
        *,
        hypotheses: Iterable[DiscoveryHypothesis] | None = None,
        experiments: Iterable[DiscriminatingExperiment] | None = None,
        observed_result: ObservedExperimentResult | None = None,
    ) -> TensionDiscoveryReport:
        tensions = self.detector.detect(ledger, obligation_id)
        if not tensions:
            return TensionDiscoveryReport(
                obligation_id=obligation_id,
                status=DiscoveryStatus.NO_TENSION,
                tensions=[], hypotheses=[], experiments=[], recommendation=None,
                prior_probabilities={}, posterior_probabilities={},
                tension_score_before=0.0, tension_score_after=0.0, tension_reduction=0.0,
                reasons=["No independently supported contradiction was detected"],
            )
        tension = max(tensions, key=lambda item: item.score)
        hypothesis_list = list(hypotheses or self.generator.generate(tension))
        for hypothesis in hypothesis_list:
            if hypothesis.tension_id in {"", "pending"}:
                hypothesis.tension_id = tension.tension_id
        if not hypothesis_list:
            return TensionDiscoveryReport(
                obligation_id=obligation_id,
                status=DiscoveryStatus.UNRESOLVED,
                tensions=tensions, hypotheses=[], experiments=[], recommendation=None,
                prior_probabilities={}, posterior_probabilities={},
                tension_score_before=tension.score, tension_score_after=tension.score, tension_reduction=0.0,
                reasons=["Tension detected but no explanatory hypothesis is available"],
            )
        priors = _normalize({item.hypothesis_id: item.prior for item in hypothesis_list})
        for item in hypothesis_list:
            item.prior = priors[item.hypothesis_id]
        experiment_list = list(experiments or self.designer.default_experiments(hypothesis_list))
        hypothesis_ids = {item.hypothesis_id for item in hypothesis_list}
        for experiment in experiment_list:
            if len(experiment.outcomes) < 2:
                raise ValueError("A discriminating experiment requires at least two outcomes")
            for hypothesis_id in hypothesis_ids:
                if hypothesis_id not in experiment.likelihoods:
                    raise ValueError(f"Missing likelihoods for hypothesis {hypothesis_id}")
                values = experiment.likelihoods[hypothesis_id]
                if set(values) != set(experiment.outcomes):
                    raise ValueError(f"Likelihood outcomes do not match experiment outcomes for {hypothesis_id}")
                if any(value < 0 or value > 1 for value in values.values()):
                    raise ValueError("Experiment likelihoods must be between zero and one")
                if not math.isclose(sum(values.values()), 1.0, rel_tol=1e-6, abs_tol=1e-6):
                    raise ValueError(f"Experiment likelihoods must sum to one for {hypothesis_id}")
        recommendation = self.designer.recommend(hypothesis_list, experiment_list)
        posterior = dict(priors)
        score_after = tension.score
        status = DiscoveryStatus.EXPERIMENT_RECOMMENDED if recommendation else DiscoveryStatus.TENSION_DETECTED
        reasons = [
            "Independent supporting and refuting evidence creates an obligation tension",
            "Hypotheses are ranked by predicted resolution relative to explanatory burden",
        ]
        if observed_result:
            chosen = next((item for item in experiment_list if item.experiment_id == observed_result.experiment_id), None)
            if chosen is None:
                raise ValueError(f"Observed experiment not found: {observed_result.experiment_id}")
            posterior = self.designer.posterior(hypothesis_list, chosen, observed_result.outcome)
            prior_entropy = _entropy(priors)
            posterior_entropy = _entropy(posterior)
            remaining_fraction = posterior_entropy / prior_entropy if prior_entropy > 0 else 0.0
            score_after = round(tension.score * min(1.0, remaining_fraction), 6)
            status = DiscoveryStatus.TENSION_REDUCED if score_after < tension.score else DiscoveryStatus.UNRESOLVED
            reasons.append("Observed result updated hypothesis probabilities and measured tension reduction")
        reduction = round(max(0.0, tension.score - score_after), 6)
        return TensionDiscoveryReport(
            obligation_id=obligation_id,
            status=status,
            tensions=tensions,
            hypotheses=hypothesis_list,
            experiments=experiment_list,
            recommendation=recommendation,
            prior_probabilities={key: round(value, 6) for key, value in priors.items()},
            posterior_probabilities={key: round(value, 6) for key, value in posterior.items()},
            tension_score_before=tension.score,
            tension_score_after=score_after,
            tension_reduction=reduction,
            reasons=reasons,
            observed_result=observed_result,
        )
