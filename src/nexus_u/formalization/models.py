from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
import time
import uuid


class FormalizationStatus(StrEnum):
    GENERATED = "GENERATED"
    SPECIALIZED_CHECKER_VERIFIED = "SPECIALIZED_CHECKER_VERIFIED"
    PROOF_ASSISTANT_READY = "PROOF_ASSISTANT_READY"
    KERNEL_VERIFIED = "KERNEL_VERIFIED"
    BLOCKED = "BLOCKED"


class ObligationStatus(StrEnum):
    OPEN = "OPEN"
    DISCHARGED = "DISCHARGED"
    EXTERNAL_REQUIRED = "EXTERNAL_REQUIRED"
    BLOCKED = "BLOCKED"


@dataclass(slots=True)
class FormalizationObligation:
    obligation_id: str
    statement: str
    category: str
    dependencies: list[str] = field(default_factory=list)
    status: ObligationStatus = ObligationStatus.OPEN
    evidence: list[str] = field(default_factory=list)
    scope: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SpecializedProofCertificate:
    certificate_id: str
    theorem_id: str
    theorem_statement: str
    machine_model: str
    parameter_domain: dict[str, Any]
    input_width: str
    lower_bound: str
    witness: dict[str, str]
    sensitivity_classes: list[dict[str, Any]]
    trusted_rules: list[str]
    proof_steps: list[dict[str, Any]]
    status: FormalizationStatus = FormalizationStatus.GENERATED
    checker_version: str = "nexus-dt-kernel-v1"
    checker_digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CertificateCheck:
    valid: bool
    status: FormalizationStatus
    errors: list[str]
    discharged_rules: list[str]
    checker_digest: str
    mutation_resistance: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FormalizedLowerBoundReport:
    challenge_id: str
    certificate: SpecializedProofCertificate
    certificate_check: CertificateCheck
    theorem_target: dict[str, Any]
    transposition_plan: list[FormalizationObligation]
    summary: dict[str, Any]
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/formalized-lower-bound-search/v1",
            "run_id": self.run_id,
            "created_at": self.created_at,
            "challenge_id": self.challenge_id,
            "certificate": self.certificate.to_dict(),
            "certificate_check": self.certificate_check.to_dict(),
            "theorem_target": self.theorem_target,
            "transposition_plan": [item.to_dict() for item in self.transposition_plan],
            "summary": self.summary,
        }
