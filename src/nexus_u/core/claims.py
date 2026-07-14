from __future__ import annotations

from .models import Claim, EpistemicStatus


RANK: dict[EpistemicStatus, int] = {
    EpistemicStatus.UNKNOWN: 0,
    EpistemicStatus.SPECULATIVE_HYPOTHESIS: 1,
    EpistemicStatus.HEURISTIC_STRATEGY: 2,
    EpistemicStatus.FORMALIZATION_TARGET: 3,
    EpistemicStatus.EMPIRICAL_SUPPORT: 4,
    EpistemicStatus.COMPUTATIONAL_EVIDENCE: 5,
    EpistemicStatus.EXECUTION_VERIFIED: 6,
    EpistemicStatus.CONDITIONAL_THEOREM: 7,
    EpistemicStatus.MATHEMATICALLY_DERIVED: 8,
    EpistemicStatus.KERNEL_VERIFIED: 9,
    EpistemicStatus.INDEPENDENTLY_REPRODUCED: 10,
    EpistemicStatus.REFUTED: 11,
}


EVIDENCE_CAP: dict[str, EpistemicStatus] = {
    "none": EpistemicStatus.UNKNOWN,
    "heuristic": EpistemicStatus.HEURISTIC_STRATEGY,
    "formal_target": EpistemicStatus.FORMALIZATION_TARGET,
    "empirical": EpistemicStatus.EMPIRICAL_SUPPORT,
    "computation": EpistemicStatus.COMPUTATIONAL_EVIDENCE,
    "execution": EpistemicStatus.EXECUTION_VERIFIED,
    "conditional_proof": EpistemicStatus.CONDITIONAL_THEOREM,
    "derivation": EpistemicStatus.MATHEMATICALLY_DERIVED,
    "kernel": EpistemicStatus.KERNEL_VERIFIED,
    "reproduction": EpistemicStatus.INDEPENDENTLY_REPRODUCED,
    "counterexample": EpistemicStatus.REFUTED,
}


def strongest_evidence_status(claim: Claim) -> EpistemicStatus:
    if not claim.evidence:
        return EpistemicStatus.UNKNOWN
    caps = [EVIDENCE_CAP.get(e.kind, EpistemicStatus.UNKNOWN) for e in claim.evidence]
    return max(caps, key=lambda status: RANK[status])


def assign_status(claim: Claim) -> EpistemicStatus:
    if not claim.evidence:
        claim.assigned_status = EpistemicStatus.UNKNOWN
        if claim.requested_status != EpistemicStatus.UNKNOWN:
            claim.missing_obligations.append("No evidence supplied for requested status")
        return claim.assigned_status

    cap = strongest_evidence_status(claim)
    requested = claim.requested_status

    if requested == EpistemicStatus.REFUTED and cap == EpistemicStatus.REFUTED:
        claim.assigned_status = EpistemicStatus.REFUTED
    elif RANK[requested] <= RANK[cap]:
        claim.assigned_status = requested
    else:
        claim.assigned_status = cap
        claim.missing_obligations.append(
            f"Requested {requested}; strongest evidence supports {cap}"
        )
    return claim.assigned_status
