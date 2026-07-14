from __future__ import annotations

import hashlib
import json
from typing import Iterable

from nexus_u.security.signing import hmac_sign, hmac_verify

from .models import (
    ActorRole,
    EvidenceSubmission,
    EvidenceVerdict,
    FederationActor,
    FederationDecision,
    FederationDecisionStatus,
    QuorumPolicy,
)


class FederationError(ValueError):
    pass


class FederationLedger:
    """Signed, multi-organization evidence ledger.

    HMAC is used only as a deterministic local reference implementation. In a
    production federation, actor secrets should be replaced with asymmetric
    signatures or an external identity provider through an adapter.
    """

    def __init__(self) -> None:
        self.actors: dict[str, FederationActor] = {}
        self._actor_secrets: dict[str, str] = {}
        self.submissions: dict[str, EvidenceSubmission] = {}
        self.dependencies: dict[str, bool] = {}

    def register_actor(self, actor: FederationActor, *, secret: str) -> None:
        if actor.actor_id in self.actors:
            raise FederationError(f"Actor already registered: {actor.actor_id}")
        if actor.trust_weight <= 0:
            raise FederationError("Actor trust weight must be positive")
        self.actors[actor.actor_id] = actor
        self._actor_secrets[actor.actor_id] = secret

    def mark_dependency(self, dependency_id: str, satisfied: bool = True) -> None:
        self.dependencies[dependency_id] = bool(satisfied)

    @staticmethod
    def digest_evidence(value: object) -> str:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def sign_submission(self, submission: EvidenceSubmission) -> EvidenceSubmission:
        actor = self.actors.get(submission.actor_id)
        if actor is None or not actor.active:
            raise FederationError("Unknown or inactive actor")
        if actor.organization_id != submission.organization_id:
            raise FederationError("Actor organization mismatch")
        secret = self._actor_secrets[actor.actor_id]
        submission.key_id = actor.key_id
        submission.signature = hmac_sign(submission.signing_payload(), secret)
        return submission

    def verify_submission(self, submission: EvidenceSubmission) -> tuple[bool, list[str]]:
        errors: list[str] = []
        actor = self.actors.get(submission.actor_id)
        if actor is None:
            return False, ["Unknown actor"]
        if not actor.active:
            errors.append("Inactive actor")
        if actor.organization_id != submission.organization_id:
            errors.append("Organization mismatch")
        if submission.key_id != actor.key_id:
            errors.append("Key identifier mismatch")
        if not submission.signature:
            errors.append("Missing signature")
        else:
            secret = self._actor_secrets.get(actor.actor_id)
            if secret is None or not hmac_verify(submission.signing_payload(), submission.signature, secret):
                errors.append("Signature mismatch")
        if not submission.evidence_digest or len(submission.evidence_digest) != 64:
            errors.append("Invalid evidence digest")
        if not submission.provenance_group:
            errors.append("Missing provenance group")
        if submission.scope not in actor.authority_scopes and "*" not in actor.authority_scopes:
            errors.append("Actor lacks authority for scope")
        return not errors, errors

    def submit(self, submission: EvidenceSubmission) -> EvidenceSubmission:
        if not submission.signature:
            self.sign_submission(submission)
        valid, errors = self.verify_submission(submission)
        if not valid:
            raise FederationError("; ".join(errors))
        self.submissions[submission.submission_id] = submission
        return submission

    def evidence_for(self, obligation_id: str) -> list[EvidenceSubmission]:
        return sorted(
            [item for item in self.submissions.values() if item.obligation_id == obligation_id],
            key=lambda item: item.created_at,
        )

    def evaluate(self, obligation_id: str, policy: QuorumPolicy) -> FederationDecision:
        evidence = self.evidence_for(obligation_id)
        valid: list[EvidenceSubmission] = []
        invalid_reasons: list[str] = []
        for item in evidence:
            ok, errors = self.verify_submission(item)
            if ok:
                valid.append(item)
            else:
                invalid_reasons.append(f"{item.submission_id}: {', '.join(errors)}")

        supporting = [item for item in valid if item.verdict == EvidenceVerdict.SUPPORTS]
        refuting = [item for item in valid if item.verdict == EvidenceVerdict.REFUTES]
        inconclusive = [item for item in valid if item.verdict == EvidenceVerdict.INCONCLUSIVE]

        reasons: list[str] = list(invalid_reasons)
        missing_dependencies = [
            dependency for dependency in policy.required_dependencies if not self.dependencies.get(dependency, False)
        ]
        if missing_dependencies:
            reasons.append("Missing required cross-system dependencies")
            return self._decision(
                obligation_id, policy, FederationDecisionStatus.MISSING_DEPENDENCY, reasons,
                supporting, refuting, inconclusive, missing_dependencies=missing_dependencies,
            )

        if supporting and refuting and policy.require_no_conflicts:
            reasons.append("Conflicting signed evidence exists")
            return self._decision(
                obligation_id, policy, FederationDecisionStatus.CONFLICT, reasons,
                supporting, refuting, inconclusive,
            )

        vetoes: list[EvidenceSubmission] = []
        for item in refuting:
            actor = self.actors[item.actor_id]
            if set(actor.roles).intersection(policy.veto_roles):
                vetoes.append(item)
        if vetoes:
            reasons.append("A veto-authorized actor submitted refuting evidence")
            return self._decision(
                obligation_id, policy, FederationDecisionStatus.BLOCKED, reasons,
                supporting, refuting, inconclusive,
            )

        organizations = {item.organization_id for item in supporting}
        independent_groups = {item.provenance_group for item in supporting}
        total_weight = sum(self.actors[item.actor_id].trust_weight for item in supporting)
        roles_present = {role for item in supporting for role in self.actors[item.actor_id].roles}
        missing_roles = [role.value for role in policy.required_roles if role not in roles_present]

        if refuting:
            reasons.append("Refuting evidence remains unresolved")
        if len(organizations) < policy.minimum_organizations:
            reasons.append(f"Organization quorum not met: {len(organizations)}/{policy.minimum_organizations}")
        if len(independent_groups) < policy.minimum_independent_evidence:
            reasons.append(
                f"Independent evidence quorum not met: {len(independent_groups)}/{policy.minimum_independent_evidence}"
            )
        if total_weight < policy.minimum_weight:
            reasons.append(f"Trust weight quorum not met: {total_weight:.3f}/{policy.minimum_weight:.3f}")
        if missing_roles:
            reasons.append(f"Missing required roles: {', '.join(missing_roles)}")
        if inconclusive and not policy.allow_inconclusive:
            reasons.append("Inconclusive evidence is not permitted by policy")

        if reasons:
            return self._decision(
                obligation_id, policy, FederationDecisionStatus.INSUFFICIENT_QUORUM, reasons,
                supporting, refuting, inconclusive, missing_roles=missing_roles,
            )
        return self._decision(
            obligation_id, policy, FederationDecisionStatus.APPROVED,
            ["Federated quorum and independence requirements satisfied"],
            supporting, refuting, inconclusive,
        )

    def _decision(
        self,
        obligation_id: str,
        policy: QuorumPolicy,
        status: FederationDecisionStatus,
        reasons: list[str],
        supporting: Iterable[EvidenceSubmission],
        refuting: Iterable[EvidenceSubmission],
        inconclusive: Iterable[EvidenceSubmission],
        *,
        missing_roles: list[str] | None = None,
        missing_dependencies: list[str] | None = None,
    ) -> FederationDecision:
        supporting = list(supporting)
        refuting = list(refuting)
        inconclusive = list(inconclusive)
        organizations = sorted({item.organization_id for item in supporting})
        groups = sorted({item.provenance_group for item in supporting})
        weight = sum(self.actors[item.actor_id].trust_weight for item in supporting)
        return FederationDecision(
            obligation_id=obligation_id,
            policy_id=policy.policy_id,
            status=status,
            reasons=reasons,
            supporting_submissions=[item.submission_id for item in supporting],
            refuting_submissions=[item.submission_id for item in refuting],
            inconclusive_submissions=[item.submission_id for item in inconclusive],
            participating_organizations=organizations,
            independent_evidence_groups=groups,
            total_weight=weight,
            missing_roles=missing_roles or [],
            missing_dependencies=missing_dependencies or [],
        )
