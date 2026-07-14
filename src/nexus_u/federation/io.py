from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ledger import FederationLedger
from .models import ActorRole, EvidenceSubmission, EvidenceVerdict, FederationActor, QuorumPolicy


def load_federation_spec(source: str | Path | dict[str, Any]) -> tuple[FederationLedger, str, QuorumPolicy]:
    raw = source if isinstance(source, dict) else json.loads(Path(source).read_text(encoding="utf-8"))
    ledger = FederationLedger()
    for item in raw.get("actors", []):
        actor = FederationActor(
            actor_id=str(item["actor_id"]),
            organization_id=str(item["organization_id"]),
            roles=[ActorRole(str(role)) for role in item.get("roles", [])],
            key_id=str(item.get("key_id", f"{item['actor_id']}-key")),
            trust_weight=float(item.get("trust_weight", 1.0)),
            authority_scopes=list(item.get("authority_scopes", ["*"])),
            active=bool(item.get("active", True)),
            metadata=dict(item.get("metadata", {})),
        )
        ledger.register_actor(actor, secret=str(item["secret"]))
    for dependency, satisfied in raw.get("dependencies", {}).items():
        ledger.mark_dependency(str(dependency), bool(satisfied))
    obligation_id = str(raw["obligation_id"])
    for item in raw.get("submissions", []):
        evidence_value = item.get("evidence", {"summary": item.get("summary", "")})
        submission = EvidenceSubmission(
            obligation_id=obligation_id,
            actor_id=str(item["actor_id"]),
            organization_id=str(item["organization_id"]),
            verdict=EvidenceVerdict(str(item["verdict"])),
            evidence_kind=str(item.get("evidence_kind", "external")),
            summary=str(item.get("summary", "")),
            evidence_digest=str(item.get("evidence_digest") or ledger.digest_evidence(evidence_value)),
            provenance_group=str(item["provenance_group"]),
            scope=str(item.get("scope", "global")),
            repository=item.get("repository"),
            commit=item.get("commit"),
            metadata=dict(item.get("metadata", {})),
        )
        ledger.submit(submission)
    p = raw.get("policy", {})
    policy = QuorumPolicy(
        policy_id=str(p.get("policy_id", "federation-policy")),
        minimum_organizations=int(p.get("minimum_organizations", 2)),
        minimum_weight=float(p.get("minimum_weight", 2.0)),
        minimum_independent_evidence=int(p.get("minimum_independent_evidence", 2)),
        required_roles=[ActorRole(str(role)) for role in p.get("required_roles", [])],
        veto_roles=[ActorRole(str(role)) for role in p.get("veto_roles", [ActorRole.SECURITY.value])],
        allow_inconclusive=bool(p.get("allow_inconclusive", True)),
        require_no_conflicts=bool(p.get("require_no_conflicts", True)),
        required_dependencies=[str(item) for item in p.get("required_dependencies", [])],
    )
    return ledger, obligation_id, policy
