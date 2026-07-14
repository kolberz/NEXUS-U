from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any

from .claims import RANK, strongest_evidence_status
from .models import ArtifactRecord, EpistemicStatus, TaskMode, TaskSpec


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    phase: str
    policy_id: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_approvals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "phase": self.phase,
            "policy_id": self.policy_id,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "required_approvals": list(self.required_approvals),
        }


DEFAULT_POLICY: dict[str, Any] = {
    "policy_id": "nexus-u-default-v1",
    "allowed_adapters": ["document", "python", "discovery", "lean", "dafny"],
    "deny_unknown_adapters": False,
    "max_unresolved_obligations_for_release": 0,
    "minimum_status_by_mode": {
        "FORMAL_PROOF": "KERNEL_VERIFIED",
        "SOFTWARE_ENGINEERING": "EXECUTION_VERIFIED",
        "EXPERIMENTAL_RESEARCH": "COMPUTATIONAL_EVIDENCE",
        "POLICY_AND_COMPLIANCE": "EXECUTION_VERIFIED"
    },
    "high_risk": {
        "require_approval": True,
        "approval_roles": ["safety_owner"],
        "input_flag": "high_risk"
    },
    "deny_output_patterns": ["sorry", "admit"],
    "require_provenance": True,
    "require_audit_chain": True
}


def load_policy(path: Path | str | None = None) -> dict[str, Any]:
    if path is None:
        return json.loads(json.dumps(DEFAULT_POLICY))
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    merged = json.loads(json.dumps(DEFAULT_POLICY))
    for key, value in raw.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return merged


class PolicyEngine:
    def __init__(self, policy: dict[str, Any] | None = None) -> None:
        self.policy = policy or load_policy()
        self.policy_id = str(self.policy.get("policy_id", "unnamed-policy"))

    def evaluate_preflight(self, task: TaskSpec, available_adapters: list[str]) -> PolicyDecision:
        reasons: list[str] = []
        warnings: list[str] = []
        approvals: list[str] = []
        allowed = set(self.policy.get("allowed_adapters", []))
        if self.policy.get("deny_unknown_adapters", False) and task.adapter not in allowed:
            reasons.append(f"Adapter {task.adapter!r} is not allowed by policy")
        if task.adapter not in available_adapters:
            reasons.append(f"Adapter {task.adapter!r} is unavailable")
        high = self.policy.get("high_risk", {})
        flag = str(high.get("input_flag", "high_risk"))
        if bool(task.inputs.get(flag, False)) and high.get("require_approval", True):
            supplied = task.inputs.get("approvals", [])
            supplied_roles = {str(item.get("role")) for item in supplied if isinstance(item, dict)}
            for role in high.get("approval_roles", []):
                if role not in supplied_roles:
                    approvals.append(str(role))
            if approvals:
                reasons.append("High-risk task is missing required approvals")
        if not task.assumptions:
            warnings.append("No assumptions declared")
        return PolicyDecision(not reasons, "preflight", self.policy_id, reasons, warnings, approvals)

    def evaluate_release(self, task: TaskSpec, record: ArtifactRecord) -> PolicyDecision:
        reasons: list[str] = []
        warnings: list[str] = []
        limit = int(self.policy.get("max_unresolved_obligations_for_release", 0))
        if len(record.unresolved_obligations) > limit:
            reasons.append(
                f"Unresolved obligations {len(record.unresolved_obligations)} exceed release limit {limit}"
            )
        output_text = json.dumps(record.output, sort_keys=True, default=str).lower()
        if TaskMode.FORMAL_PROOF in task.modes:
            for pattern in self.policy.get("deny_output_patterns", []):
                if str(pattern).lower() in output_text:
                    reasons.append(f"Denied output pattern detected: {pattern}")
        if not record.claims:
            reasons.append("No claim record was generated")
        else:
            actual = strongest_evidence_status(record.claims[0])
            requirements = self.policy.get("minimum_status_by_mode", {})
            required_statuses: list[EpistemicStatus] = []
            for mode in task.modes:
                raw = requirements.get(str(mode)) or requirements.get(getattr(mode, "value", str(mode)))
                if raw:
                    required_statuses.append(EpistemicStatus(raw))
            if required_statuses:
                required = max(required_statuses, key=lambda status: RANK[status])
                if RANK[actual] < RANK[required]:
                    reasons.append(f"Evidence status {actual} is below policy minimum {required}")
        if self.policy.get("require_audit_chain", True) and not record.audit_root:
            warnings.append("Audit root is not yet assigned; it must be present in the final bundle")
        return PolicyDecision(not reasons, "release", self.policy_id, reasons, warnings)
