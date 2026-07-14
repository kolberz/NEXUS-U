from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from .models import ClaimStatus, EvidenceKind, ObstructionKind
from .search_models import (
    ActiveSearchReport,
    AttackKind,
    ProofRouteCandidate,
    ProofRouteKind,
    RankedRoute,
    RestrictedLemmaCertificate,
    RouteAttack,
    RouteStatus,
)


class ActiveLowerBoundSearchEngine:
    """Obligation-weighted proof-route search for lower-bound research.

    This engine does not claim the open universal lower bound. It creates
    explicitly scoped proof routes, attacks them before ranking, derives a
    small restricted-model theorem with a checkable symbolic certificate, and
    prioritizes routes by expected obligation reduction rather than novelty.
    """

    def run(
        self,
        challenge: dict[str, Any],
        routes: list[dict[str, Any]] | None = None,
        *,
        max_certificate_n: int = 16,
    ) -> ActiveSearchReport:
        raw_routes = routes if routes is not None else self.load_builtin_routes()
        candidates = [self._candidate(item) for item in raw_routes]
        attacks = [self.attack(candidate, challenge) for candidate in candidates]
        certificate = self._query_lower_bound_certificate(max_certificate_n)
        rankings = self._rank(candidates, attacks, certificate)
        attack_by_id = {item.route_id: item for item in attacks}
        blocked = [item for item in attacks if not item.survives]
        surviving = [item for item in attacks if item.survives]
        formalization_ready = [item for item in attacks if item.status == RouteStatus.FORMALIZATION_READY]
        derived = [item for item in attacks if item.status == RouteStatus.DERIVED_RESTRICTED]
        universal_claims = [
            item for item in candidates
            if item.target_problem_id == "integer_multiplication_offline"
            and item.target_complexity == "Omega(n log n)"
            and item.requested_status in {ClaimStatus.PROVED, ClaimStatus.PUBLISHED_RESULT}
        ]
        false_universal_promotions = [
            item.route_id for item in universal_claims if attack_by_id[item.route_id].status not in {RouteStatus.BLOCKED, RouteStatus.CONDITIONAL}
        ]
        top = rankings[0] if rankings else None
        summary = {
            "candidate_count": len(candidates),
            "blocked_count": len(blocked),
            "surviving_count": len(surviving),
            "formalization_ready_count": len(formalization_ready),
            "derived_restricted_count": len(derived),
            "restricted_query_certificate_valid": self._certificate_valid(certificate, max_certificate_n),
            "restricted_query_bound": certificate.bound,
            "universal_offline_lower_bound_status": "OPEN",
            "false_universal_promotions": false_universal_promotions,
            "no_false_solution_claim": not false_universal_promotions,
            "top_route_id": top.route_id if top else None,
            "top_route_status": top.status.value if top else None,
            "top_route_score": top.score if top else 0.0,
            "total_expected_obligation_reduction": round(sum(item.expected_obligation_reduction for item in rankings[:5]), 6),
            "active_search_status": "RESTRICTED_PROGRESS_WITH_OPEN_UNIVERSAL_TARGET",
        }
        return ActiveSearchReport(
            challenge_id=str(challenge.get("challenge_id", "integer-multiplication-optimality")),
            candidates=candidates,
            attacks=attacks,
            rankings=rankings,
            certificates=[certificate],
            summary=summary,
        )

    @staticmethod
    def builtin_routes_path() -> Path:
        return Path(str(files("nexus_u.lower_bounds").joinpath("data/active-search-routes.json")))

    @classmethod
    def load_builtin_routes(cls) -> list[dict[str, Any]]:
        return json.loads(cls.builtin_routes_path().read_text(encoding="utf-8"))["routes"]

    @staticmethod
    def _candidate(raw: dict[str, Any]) -> ProofRouteCandidate:
        return ProofRouteCandidate(
            **{
                **raw,
                "kind": ProofRouteKind(raw["kind"]),
                "requested_status": ClaimStatus(raw["requested_status"]),
                "evidence_kind": EvidenceKind(raw["evidence_kind"]),
            }
        )

    def attack(self, candidate: ProofRouteCandidate, challenge: dict[str, Any]) -> RouteAttack:
        attacks: list[AttackKind] = []
        obstructions: list[ObstructionKind] = []
        reasons: list[str] = []
        metadata = candidate.metadata

        if candidate.kind == ProofRouteKind.EMPIRICAL_EXTRAPOLATION or (
            candidate.evidence_kind in {EvidenceKind.EMPIRICAL_TIMING, EvidenceKind.FINITE_TESTS}
            and not metadata.get("symbolic_derivation")
        ):
            attacks.append(AttackKind.EMPIRICAL_ONLY)
            obstructions.append(ObstructionKind.EMPIRICAL_TO_ASYMPTOTIC_GAP)
            reasons.append("Finite observations cannot establish a universal asymptotic lower bound.")
        if metadata.get("source_model_id") and metadata.get("source_model_id") != candidate.target_model_id and not metadata.get("proved_model_transfer"):
            attacks.append(AttackKind.MODEL_SCOPE)
            obstructions.append(ObstructionKind.MODEL_MISMATCH)
            reasons.append("The route changes machine model without a proved transfer theorem.")
        if metadata.get("online_to_offline"):
            attacks.append(AttackKind.MODEL_SCOPE)
            obstructions.append(ObstructionKind.ONLINE_OFFLINE_GAP)
            reasons.append("An online lower bound cannot be promoted to the offline target without a transfer proof.")
        if metadata.get("restricted_scope") and metadata.get("universalize"):
            attacks.append(AttackKind.UNIVERSALIZATION)
            obstructions.append(ObstructionKind.RESTRICTED_TO_UNIVERSAL_GAP)
            reasons.append("A restricted-model result is being universalized.")
        if candidate.kind == ProofRouteKind.INFORMATION_COUNTING:
            attacks.append(AttackKind.INFORMATION_COST_GAP)
            obstructions.append(ObstructionKind.INFORMATION_COUNTING_TOO_WEAK)
            reasons.append("Information volume alone does not force the required time or data movement.")
            if not metadata.get("reversibility_accounted"):
                attacks.append(AttackKind.REVERSIBILITY)
                obstructions.append(ObstructionKind.REVERSIBILITY_ESCAPE)
                reasons.append("The route ignores reversible computation and uncomputation.")
        if metadata.get("depends_on_open_premise"):
            attacks.append(AttackKind.OPEN_PREMISE)
            obstructions.append(ObstructionKind.REDUCTION_PREMISE_OPEN)
            reasons.append("The route is valuable but remains conditional on an open lower bound.")
        if metadata.get("reduction_overhead_unchecked"):
            attacks.append(AttackKind.REDUCTION_OVERHEAD)
            obstructions.append(ObstructionKind.REDUCTION_OVERHEAD)
            reasons.append("The reduction overhead is not yet strong enough to preserve the target bound.")
        if metadata.get("tautological"):
            attacks.append(AttackKind.TAUTOLOGY)
            reasons.append("The proposed lemma restates the target instead of reducing proof debt.")
        if not candidate.mechanism.strip():
            attacks.append(AttackKind.MISSING_MECHANISM)
            reasons.append("The route has no explicit mechanism connecting assumptions to the lower bound.")
        if not candidate.falsification_tests:
            attacks.append(AttackKind.MISSING_FALSIFICATION)
            reasons.append("The route lacks an adversarial test capable of exposing a false premise.")

        hard = {
            AttackKind.MODEL_SCOPE,
            AttackKind.EMPIRICAL_ONLY,
            AttackKind.REVERSIBILITY,
            AttackKind.INFORMATION_COST_GAP,
            AttackKind.UNIVERSALIZATION,
            AttackKind.TAUTOLOGY,
            AttackKind.MISSING_MECHANISM,
        }
        survives = not any(item in hard for item in attacks)
        if not survives:
            status = RouteStatus.BLOCKED
        elif candidate.route_id == "query_model_read_all_bits":
            status = RouteStatus.DERIVED_RESTRICTED
        elif candidate.kind in {ProofRouteKind.FORMALIZE_REDUCTION, ProofRouteKind.BARRIER_THEOREM} and not metadata.get("depends_on_open_premise"):
            status = RouteStatus.FORMALIZATION_READY
        elif AttackKind.OPEN_PREMISE in attacks or candidate.proof_obligations:
            status = RouteStatus.CONDITIONAL
        else:
            status = RouteStatus.PROPOSED
        debt = round(
            0.12 * len(candidate.proof_obligations)
            + 0.15 * len(attacks)
            + 0.1 * len(candidate.assumptions)
            + (0.5 if metadata.get("depends_on_open_premise") else 0.0),
            6,
        )
        if not reasons:
            reasons.append("No blocking scope, evidence, reversibility, or mechanism defect was found.")
        return RouteAttack(
            route_id=candidate.route_id,
            attacks=sorted(set(attacks), key=lambda item: item.value),
            inherited_obstructions=sorted(set(obstructions), key=lambda item: item.value),
            reasons=reasons,
            survives=survives,
            status=status,
            obligation_debt=debt,
        )

    def _rank(
        self,
        candidates: list[ProofRouteCandidate],
        attacks: list[RouteAttack],
        certificate: RestrictedLemmaCertificate,
    ) -> list[RankedRoute]:
        attack_by_id = {item.route_id: item for item in attacks}
        ranked: list[RankedRoute] = []
        status_factor = {
            RouteStatus.DERIVED_RESTRICTED: 1.0,
            RouteStatus.FORMALIZATION_READY: 0.9,
            RouteStatus.PROPOSED: 0.75,
            RouteStatus.CONDITIONAL: 0.62,
            RouteStatus.BLOCKED: 0.0,
            RouteStatus.REFUTED: 0.0,
        }
        for candidate in candidates:
            attack = attack_by_id[candidate.route_id]
            factor = status_factor[attack.status]
            reduction = max(0.0, candidate.leverage * candidate.tractability * factor - 0.35 * attack.obligation_debt)
            score = (
                0.38 * candidate.leverage
                + 0.18 * candidate.novelty
                + 0.28 * candidate.tractability
                - 0.18 * candidate.estimated_cost
                - 0.42 * attack.obligation_debt
            ) * factor
            if candidate.route_id == "query_model_read_all_bits" and self._certificate_valid(certificate, len(certificate.verified_instances)):
                score += 0.12
                reduction += 0.15
            rationale = [
                f"Leverage={candidate.leverage}",
                f"Novelty={candidate.novelty}",
                f"Tractability={candidate.tractability}",
                f"EstimatedCost={candidate.estimated_cost}",
                f"ObligationDebt={attack.obligation_debt}",
            ]
            if attack.status == RouteStatus.BLOCKED:
                rationale.append("Blocked routes receive zero discovery priority.")
            elif attack.status == RouteStatus.DERIVED_RESTRICTED:
                rationale.append("A correct restricted theorem discharges a real but scoped obligation.")
            elif attack.status == RouteStatus.FORMALIZATION_READY:
                rationale.append("The route is ready for machine-checking without pretending to prove an open premise.")
            elif attack.status == RouteStatus.CONDITIONAL:
                rationale.append("The route remains useful only with its unresolved premises visible.")
            ranked.append(RankedRoute(
                route_id=candidate.route_id,
                title=candidate.title,
                status=attack.status,
                score=round(max(0.0, score), 6),
                expected_obligation_reduction=round(reduction, 6),
                obligation_debt=attack.obligation_debt,
                rationale=rationale,
            ))
        return sorted(ranked, key=lambda item: (-item.score, item.route_id))

    @staticmethod
    def _query_lower_bound_certificate(max_n: int) -> RestrictedLemmaCertificate:
        if max_n < 1:
            raise ValueError("max_certificate_n must be positive")
        verified: list[dict[str, Any]] = []
        for n in range(1, max_n + 1):
            x = y = (1 << n) - 1
            base = x * y
            sensitive_x = all(((x ^ (1 << bit)) * y) != base for bit in range(n))
            sensitive_y = all((x * (y ^ (1 << bit))) != base for bit in range(n))
            verified.append({
                "n": n,
                "witness_x": x,
                "witness_y": y,
                "sensitive_bits": 2 * n if sensitive_x and sensitive_y else 0,
                "valid": sensitive_x and sensitive_y,
            })
        return RestrictedLemmaCertificate(
            certificate_id="query-sensitivity-lower-bound-v1",
            theorem=(
                "Any deterministic bit-query decision tree computing exact multiplication of two n-bit integers "
                "has worst-case query depth at least 2n."
            ),
            machine_model="deterministic adaptive bit-query decision tree",
            bound="Omega(n) with exact depth lower bound 2n",
            witness="x = y = 2^n - 1",
            proof_steps=[
                "At x = y = 2^n - 1, flipping any input bit of x changes the product by a nonzero multiple of y.",
                "At the same witness, flipping any input bit of y changes the product by a nonzero multiple of x.",
                "Therefore every one of the 2n input bits is sensitive at this single input.",
                "A deterministic decision-tree path that omits a sensitive bit is identical on a one-bit-flipped input but would output the wrong product.",
                "Hence the path for the witness queries all 2n bits, establishing worst-case depth at least 2n.",
            ],
            verified_instances=verified,
            status=RouteStatus.DERIVED_RESTRICTED,
            kernel_verified=False,
        )

    @staticmethod
    def _certificate_valid(certificate: RestrictedLemmaCertificate, expected_count: int) -> bool:
        return (
            certificate.status == RouteStatus.DERIVED_RESTRICTED
            and not certificate.kernel_verified
            and len(certificate.verified_instances) == expected_count
            and all(item.get("valid") and item.get("sensitive_bits") == 2 * item.get("n", 0) for item in certificate.verified_instances)
        )
