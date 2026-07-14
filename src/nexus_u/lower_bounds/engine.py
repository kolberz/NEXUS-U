from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import (
    AuditDecision,
    BoundClaim,
    BoundKind,
    CandidateAudit,
    CandidateClaim,
    ClaimStatus,
    EvidenceKind,
    LowerBoundLabReport,
    MachineModel,
    ObstructionKind,
    ProblemDefinition,
    ReductionRecord,
    ResearchAgendaItem,
    SourceRecord,
    TheoremTarget,
)


PROOF_EVIDENCE = {
    EvidenceKind.PEER_REVIEWED_PROOF,
    EvidenceKind.PUBLISHED_PROOF,
    EvidenceKind.FORMAL_PROOF,
}


class LowerBoundDiscoveryLab:
    """Model-aware lower-bound research registry and promotion firewall.

    The engine deliberately does not attempt to prove an open lower bound. It
    verifies scope, propagates proved reductions conditionally, identifies
    missing premises, and prevents weaker evidence from being promoted into a
    universal asymptotic claim.
    """

    def run(self, raw: dict[str, Any]) -> LowerBoundLabReport:
        sources = [SourceRecord(**item) for item in raw.get("sources", [])]
        models = [MachineModel(**item) for item in raw.get("machine_models", [])]
        problems = [ProblemDefinition(**item) for item in raw.get("problems", [])]
        claims = [self._claim(item) for item in raw.get("claims", [])]
        reductions = [self._reduction(item) for item in raw.get("reductions", [])]
        candidates = [self._candidate(item) for item in raw.get("candidates", [])]
        targets = [self._target(item) for item in raw.get("theorem_targets", [])]

        errors = self._validate(sources, models, problems, claims, reductions, candidates, targets)
        model_by_id = {item.model_id: item for item in models}
        problem_by_id = {item.problem_id: item for item in problems}
        claim_by_id = {item.claim_id: item for item in claims}

        derived = self._derive_reduction_claims(reductions, claims, problem_by_id)
        all_claims = claims + derived
        audits = [self.audit_candidate(item, model_by_id, problem_by_id, claim_by_id, reductions) for item in candidates]
        agenda = self._agenda(targets, all_claims, reductions)

        universal_lower = [
            c for c in all_claims
            if c.problem_id == "integer_multiplication_offline"
            and c.kind == BoundKind.LOWER
            and c.complexity == "Omega(n log n)"
        ]
        unconditional_universal = [c for c in universal_lower if c.claim_id == "offline_matching_lower_open"]
        summary = {
            "source_count": len(sources),
            "machine_model_count": len(models),
            "problem_count": len(problems),
            "claim_count": len(all_claims),
            "reduction_count": len(reductions),
            "candidate_count": len(candidates),
            "accepted_candidates": sum(a.decision in {AuditDecision.ACCEPT, AuditDecision.ACCEPT_RESTRICTED} for a in audits),
            "conditional_candidates": sum(a.decision == AuditDecision.HOLD_CONDITIONAL for a in audits),
            "rejected_promotions": sum(a.decision == AuditDecision.REJECT_PROMOTION for a in audits),
            "unconditional_universal_lower_bound_status": self._strongest_status(unconditional_universal).value,
            "best_available_lower_bound_route": self._strongest_status(universal_lower).value,
            "proved_upper_bound_present": any(
                c.problem_id == "integer_multiplication_offline"
                and c.kind == BoundKind.UPPER
                and c.complexity == "O(n log n)"
                and c.status == ClaimStatus.PROVED
                for c in all_claims
            ),
            "matrix_transposition_route_conditional": any(
                c.claim_id.startswith("derived:")
                and c.problem_id == "integer_multiplication_offline"
                and c.status == ClaimStatus.CONDITIONAL_THEOREM
                for c in all_claims
            ),
            "open_high_leverage_targets": len(agenda),
            "integrity_valid": not errors,
            "no_false_solution_claim": self._strongest_status(universal_lower) != ClaimStatus.PROVED,
        }
        return LowerBoundLabReport(
            challenge_id=str(raw.get("challenge_id", "lower-bound-challenge")),
            integrity_valid=not errors,
            integrity_errors=errors,
            claims=all_claims,
            reductions=reductions,
            audits=audits,
            agenda=agenda,
            summary=summary,
        )

    @staticmethod
    def _claim(raw: dict[str, Any]) -> BoundClaim:
        return BoundClaim(
            **{**raw, "kind": BoundKind(raw["kind"]), "status": ClaimStatus(raw["status"]), "evidence_kind": EvidenceKind(raw["evidence_kind"])}
        )

    @staticmethod
    def _reduction(raw: dict[str, Any]) -> ReductionRecord:
        return ReductionRecord(
            **{**raw, "status": ClaimStatus(raw["status"]), "evidence_kind": EvidenceKind(raw["evidence_kind"])}
        )

    @staticmethod
    def _candidate(raw: dict[str, Any]) -> CandidateClaim:
        return CandidateClaim(
            **{**raw, "requested_status": ClaimStatus(raw["requested_status"]), "evidence_kind": EvidenceKind(raw["evidence_kind"])}
        )

    @staticmethod
    def _target(raw: dict[str, Any]) -> TheoremTarget:
        return TheoremTarget(**{**raw, "target_status": ClaimStatus(raw["target_status"])})

    @staticmethod
    def _strongest_status(claims: list[BoundClaim]) -> ClaimStatus:
        order = [
            ClaimStatus.PROVED,
            ClaimStatus.PUBLISHED_RESULT,
            ClaimStatus.CONDITIONAL_THEOREM,
            ClaimStatus.EMPIRICAL,
            ClaimStatus.HEURISTIC,
            ClaimStatus.OPEN,
            ClaimStatus.UNKNOWN,
            ClaimStatus.REFUTED,
        ]
        statuses = {item.status for item in claims}
        return next((item for item in order if item in statuses), ClaimStatus.UNKNOWN)

    def _validate(
        self,
        sources: list[SourceRecord],
        models: list[MachineModel],
        problems: list[ProblemDefinition],
        claims: list[BoundClaim],
        reductions: list[ReductionRecord],
        candidates: list[CandidateClaim],
        targets: list[TheoremTarget],
    ) -> list[str]:
        errors: list[str] = []
        for label, values, key in (
            ("source", sources, "source_id"),
            ("model", models, "model_id"),
            ("problem", problems, "problem_id"),
            ("claim", claims, "claim_id"),
            ("reduction", reductions, "reduction_id"),
            ("candidate", candidates, "candidate_id"),
            ("target", targets, "target_id"),
        ):
            ids = [getattr(item, key) for item in values]
            if len(ids) != len(set(ids)):
                errors.append(f"Duplicate {label} identifier")
        source_ids = {item.source_id for item in sources}
        model_ids = {item.model_id for item in models}
        problem_ids = {item.problem_id for item in problems}
        for problem in problems:
            if problem.machine_model_id not in model_ids:
                errors.append(f"Problem {problem.problem_id} references missing model {problem.machine_model_id}")
        for claim in claims:
            if claim.problem_id not in problem_ids:
                errors.append(f"Claim {claim.claim_id} references missing problem")
            for source_id in claim.source_ids:
                if source_id not in source_ids:
                    errors.append(f"Claim {claim.claim_id} references missing source {source_id}")
        problem_map = {item.problem_id: item for item in problems}
        model_map = {item.model_id: item for item in models}
        adjacency: dict[str, list[str]] = defaultdict(list)
        for reduction in reductions:
            if reduction.source_problem_id not in problem_ids or reduction.target_problem_id not in problem_ids:
                errors.append(f"Reduction {reduction.reduction_id} references missing problem")
            else:
                adjacency[reduction.source_problem_id].append(reduction.target_problem_id)
                if reduction.model_preserving:
                    source_model = problem_map[reduction.source_problem_id].machine_model_id
                    target_model = problem_map[reduction.target_problem_id].machine_model_id
                    if source_model != target_model:
                        errors.append(
                            f"Reduction {reduction.reduction_id} claims model preservation across {source_model} and {target_model}"
                        )
            for source_id in reduction.source_ids:
                if source_id not in source_ids:
                    errors.append(f"Reduction {reduction.reduction_id} references missing source {source_id}")
        visiting: set[str] = set()
        visited: set[str] = set()
        def visit(node: str) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for nxt in adjacency.get(node, []):
                if visit(nxt):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False
        if any(visit(node) for node in list(adjacency) if node not in visited):
            errors.append("Reduction graph contains a dependency cycle")
        for candidate in candidates:
            if candidate.target_problem_id not in problem_ids:
                errors.append(f"Candidate {candidate.candidate_id} references missing target problem")
        return errors

    def _derive_reduction_claims(
        self,
        reductions: list[ReductionRecord],
        claims: list[BoundClaim],
        problems: dict[str, ProblemDefinition],
    ) -> list[BoundClaim]:
        lower_by_problem: dict[str, list[BoundClaim]] = defaultdict(list)
        for claim in claims:
            if claim.kind == BoundKind.LOWER:
                lower_by_problem[claim.problem_id].append(claim)
        derived: list[BoundClaim] = []
        for reduction in reductions:
            matching = [c for c in lower_by_problem[reduction.source_problem_id] if c.complexity == reduction.premise_bound]
            premise_proved = any(c.status in {ClaimStatus.PROVED, ClaimStatus.PUBLISHED_RESULT} for c in matching)
            if reduction.status in {ClaimStatus.PROVED, ClaimStatus.PUBLISHED_RESULT} and premise_proved:
                status = ClaimStatus.PUBLISHED_RESULT
                assumptions: list[str] = []
            else:
                status = ClaimStatus.CONDITIONAL_THEOREM
                assumptions = [
                    f"Establish {reduction.premise_bound} for {problems[reduction.source_problem_id].name}",
                    *reduction.assumptions,
                ]
            derived.append(BoundClaim(
                claim_id=f"derived:{reduction.reduction_id}",
                problem_id=reduction.target_problem_id,
                kind=BoundKind.LOWER,
                complexity=reduction.consequence_bound,
                status=status,
                evidence_kind=EvidenceKind.PROVED_REDUCTION,
                source_ids=list(reduction.source_ids),
                assumptions=assumptions,
                scope=f"Derived through {reduction.reduction_id}; model_preserving={reduction.model_preserving}",
                statement=f"{reduction.premise_bound} for {reduction.source_problem_id} implies {reduction.consequence_bound} for {reduction.target_problem_id}",
            ))
        return derived

    def audit_candidate(
        self,
        candidate: CandidateClaim,
        models: dict[str, MachineModel],
        problems: dict[str, ProblemDefinition],
        claims: dict[str, BoundClaim],
        reductions: list[ReductionRecord],
    ) -> CandidateAudit:
        obstructions: list[ObstructionKind] = []
        reasons: list[str] = []
        target_problem = problems.get(candidate.target_problem_id)
        if target_problem is None:
            return CandidateAudit(
                candidate.candidate_id, AuditDecision.REJECT_PROMOTION, ClaimStatus.UNKNOWN,
                [ObstructionKind.MISSING_SOURCE], ["The candidate references an undefined target problem."],
            )
        target_model = models.get(target_problem.machine_model_id)
        if target_model is None:
            return CandidateAudit(
                candidate.candidate_id, AuditDecision.REJECT_PROMOTION, ClaimStatus.UNKNOWN,
                [ObstructionKind.MODEL_MISMATCH], ["The target problem references an undefined machine model."],
            )

        if candidate.evidence_kind in {EvidenceKind.EMPIRICAL_TIMING, EvidenceKind.FINITE_TESTS} and candidate.requested_status in {ClaimStatus.PROVED, ClaimStatus.PUBLISHED_RESULT}:
            obstructions.append(ObstructionKind.EMPIRICAL_TO_ASYMPTOTIC_GAP)
            reasons.append("Finite timings and tests cannot prove a universal asymptotic lower bound.")
        if candidate.evidence_kind == EvidenceKind.CONSENSUS and candidate.requested_status == ClaimStatus.PROVED:
            obstructions.append(ObstructionKind.EMPIRICAL_TO_ASYMPTOTIC_GAP)
            reasons.append("Community expectation is not a proof.")
        if candidate.source_model_id and candidate.target_model_id and candidate.source_model_id != candidate.target_model_id:
            source = models.get(candidate.source_model_id)
            target = models.get(candidate.target_model_id)
            if source and target and source.online and not target.online:
                obstructions.append(ObstructionKind.ONLINE_OFFLINE_GAP)
                reasons.append("An online lower bound does not automatically transfer to offline multiplication.")
            else:
                obstructions.append(ObstructionKind.MODEL_MISMATCH)
                reasons.append("The evidence and requested theorem use different computational models.")
        if candidate.metadata.get("restricted_scope") and candidate.metadata.get("universalize"):
            obstructions.append(ObstructionKind.RESTRICTED_TO_UNIVERSAL_GAP)
            reasons.append("A restricted-model theorem cannot be advertised as a universal lower bound.")
        if candidate.evidence_kind == EvidenceKind.INFORMATION_COUNTING:
            obstructions.append(ObstructionKind.INFORMATION_COUNTING_TOO_WEAK)
            reasons.append("Input/output information count alone does not establish operation or movement cost.")
            if not candidate.metadata.get("reversibility_accounted", False):
                obstructions.append(ObstructionKind.REVERSIBILITY_ESCAPE)
                reasons.append("The argument does not account for reversible computation or uncomputation.")
        if candidate.metadata.get("circuit_result") and target_model.access_pattern == "sequential_tapes":
            obstructions.append(ObstructionKind.CIRCUIT_TO_TURING_TRANSFER_GAP)
            reasons.append("A circuit lower bound requires a proved transfer to the multitape Turing model.")
        if candidate.metadata.get("depends_on_open_premise"):
            obstructions.append(ObstructionKind.REDUCTION_PREMISE_OPEN)
            reasons.append("The proposed conclusion remains conditional on an unproved source lower bound.")
        if candidate.metadata.get("reduction_overhead_unchecked"):
            obstructions.append(ObstructionKind.REDUCTION_OVERHEAD)
            reasons.append("The size and time overhead of the reduction have not been proved small enough.")

        if obstructions:
            allowed = ClaimStatus.CONDITIONAL_THEOREM if ObstructionKind.REDUCTION_PREMISE_OPEN in obstructions and len(obstructions) == 1 else ClaimStatus.HEURISTIC
            decision = AuditDecision.HOLD_CONDITIONAL if allowed == ClaimStatus.CONDITIONAL_THEOREM else AuditDecision.REJECT_PROMOTION
        elif candidate.evidence_kind in PROOF_EVIDENCE:
            restricted = bool(candidate.metadata.get("restricted_scope"))
            decision = AuditDecision.ACCEPT_RESTRICTED if restricted else AuditDecision.ACCEPT
            allowed = candidate.requested_status
            reasons.append("Evidence class and theorem scope are aligned.")
        elif candidate.requested_status == ClaimStatus.OPEN:
            decision = AuditDecision.ACCEPT
            allowed = ClaimStatus.OPEN
            reasons.append("The candidate honestly records an open obligation.")
        else:
            decision = AuditDecision.REJECT_PROMOTION
            allowed = ClaimStatus.HEURISTIC
            reasons.append("The supplied evidence does not justify the requested status.")
        return CandidateAudit(candidate.candidate_id, decision, allowed, sorted(set(obstructions), key=lambda x: x.value), reasons)

    def _agenda(
        self,
        targets: list[TheoremTarget],
        claims: list[BoundClaim],
        reductions: list[ReductionRecord],
    ) -> list[ResearchAgendaItem]:
        proved_claims = {item.claim_id for item in claims if item.status in {ClaimStatus.PROVED, ClaimStatus.PUBLISHED_RESULT}}
        agenda: list[ResearchAgendaItem] = []
        for target in targets:
            unresolved = [item for item in target.prerequisites if item not in proved_claims]
            priority = round(target.leverage / max(0.25, target.difficulty) / (1.0 + 0.2 * len(unresolved)), 6)
            rationale = [f"Leverage={target.leverage}", f"Difficulty={target.difficulty}"]
            if unresolved:
                rationale.append(f"Unresolved prerequisites: {', '.join(unresolved)}")
            if target.target_id == "transposition_lower_bound":
                rationale.append("A matching transposition lower bound activates the proved reduction route.")
            agenda.append(ResearchAgendaItem(target.target_id, target.statement, priority, rationale, unresolved))
        return sorted(agenda, key=lambda item: (-item.priority, item.target_id))
