from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import platform
import time
import uuid
from typing import Any

from nexus_u.security.signing import hmac_sign, hmac_verify


class ReceiptVerdict(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"


class ReceiptSignatureProfile(StrEnum):
    LOCAL_REFERENCE_HMAC = "LOCAL_REFERENCE_HMAC"
    EXTERNAL_ED25519 = "EXTERNAL_ED25519"
    SIGSTORE_BUNDLE = "SIGSTORE_BUNDLE"


class KernelQuorumStatus(StrEnum):
    NO_RECEIPTS = "NO_RECEIPTS"
    INVALID_RECEIPTS = "INVALID_RECEIPTS"
    CONFLICT = "CONFLICT"
    INSUFFICIENT_QUORUM = "INSUFFICIENT_QUORUM"
    LOCAL_PROCESS_QUORUM = "LOCAL_PROCESS_QUORUM"
    FEDERATED_KERNEL_REPRODUCED = "FEDERATED_KERNEL_REPRODUCED"


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(slots=True)
class KernelReceiptRequest:
    request_id: str
    project_id: str
    theorem: str
    project_sha256: str
    source_sha256: str
    toolchain: str
    expected_version_fragment: str
    command: list[str]
    universal_target_status: str = "OPEN"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["schema"] = "https://nexus-u.dev/kernel-receipt-request/v1"
        return raw


@dataclass(slots=True)
class KernelRunnerIdentity:
    runner_id: str
    organization_id: str
    provenance_group: str
    key_id: str
    signature_profile: ReceiptSignatureProfile = ReceiptSignatureProfile.LOCAL_REFERENCE_HMAC
    platform_family: str = field(default_factory=lambda: platform.system().lower() or "unknown")
    external_independence: bool = False
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class KernelReceipt:
    request_id: str
    runner_id: str
    organization_id: str
    provenance_group: str
    key_id: str
    signature_profile: ReceiptSignatureProfile
    project_id: str
    theorem: str
    project_sha256: str
    source_sha256: str
    toolchain: str
    version_output: str
    executable_sha256: str
    command: list[str]
    returncode: int
    stdout_sha256: str
    stderr_sha256: str
    verdict: ReceiptVerdict
    platform_family: str
    environment_digest: str
    external_independence: bool = False
    receipt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    signature: str | None = None

    def signing_payload(self) -> dict[str, Any]:
        raw = asdict(self)
        raw.pop("signature", None)
        raw["signature_profile"] = str(self.signature_profile)
        raw["verdict"] = str(self.verdict)
        return raw

    def to_dict(self) -> dict[str, Any]:
        raw = self.signing_payload()
        raw["signature"] = self.signature
        raw["schema"] = "https://nexus-u.dev/kernel-receipt/v1"
        return raw


@dataclass(slots=True)
class KernelQuorumPolicy:
    policy_id: str = "kernel-quorum-v1"
    minimum_organizations: int = 2
    minimum_independent_groups: int = 2
    minimum_platform_families: int = 1
    require_no_rejections: bool = True
    require_external_signatures_for_promotion: bool = True
    required_toolchain: str = "leanprover/lean4:v4.29.1"
    expected_version_fragment: str = "4.29.1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class KernelQuorumDecision:
    request_id: str
    status: KernelQuorumStatus
    reasons: list[str]
    valid_receipts: list[str]
    invalid_receipts: dict[str, list[str]]
    organizations: list[str]
    provenance_groups: list[str]
    platform_families: list[str]
    accepted_receipts: list[str]
    rejected_receipts: list[str]
    external_independence_claimed: bool
    theorem_status: str
    universal_target_status: str = "OPEN"
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["schema"] = "https://nexus-u.dev/kernel-quorum-decision/v1"
        return raw


class KernelReceiptFederation:
    """Evidence federation for replayable external proof-kernel receipts.

    The built-in HMAC profile is deliberately a local reference profile. It can
    validate process mechanics but cannot establish external institutional
    independence. Production promotion requires externally verifiable signature
    profiles and independently administered runner identities.
    """

    def __init__(self, request: KernelReceiptRequest) -> None:
        self.request = request
        self.runners: dict[str, KernelRunnerIdentity] = {}
        self._secrets: dict[str, str] = {}
        self.receipts: dict[str, KernelReceipt] = {}

    def register_runner(self, runner: KernelRunnerIdentity, *, secret: str | None = None) -> None:
        if runner.runner_id in self.runners:
            raise ValueError(f"runner already registered: {runner.runner_id}")
        if runner.signature_profile == ReceiptSignatureProfile.LOCAL_REFERENCE_HMAC and not secret:
            raise ValueError("local HMAC runners require a secret")
        self.runners[runner.runner_id] = runner
        if secret:
            self._secrets[runner.runner_id] = secret

    def sign_local(self, receipt: KernelReceipt) -> KernelReceipt:
        runner = self.runners.get(receipt.runner_id)
        if not runner:
            raise ValueError("unknown runner")
        if runner.signature_profile != ReceiptSignatureProfile.LOCAL_REFERENCE_HMAC:
            raise ValueError("built-in signer supports only the local reference HMAC profile")
        receipt.signature = hmac_sign(receipt.signing_payload(), self._secrets[receipt.runner_id])
        return receipt

    def verify(self, receipt: KernelReceipt) -> tuple[bool, list[str]]:
        errors: list[str] = []
        runner = self.runners.get(receipt.runner_id)
        if runner is None or not runner.active:
            return False, ["unknown or inactive runner"]
        if receipt.organization_id != runner.organization_id:
            errors.append("organization mismatch")
        if receipt.provenance_group != runner.provenance_group:
            errors.append("provenance-group mismatch")
        if receipt.key_id != runner.key_id:
            errors.append("key identifier mismatch")
        if receipt.signature_profile != runner.signature_profile:
            errors.append("signature profile mismatch")
        if receipt.request_id != self.request.request_id:
            errors.append("request identifier mismatch")
        for field_name in ("project_id", "theorem", "project_sha256", "source_sha256", "toolchain"):
            if getattr(receipt, field_name) != getattr(self.request, field_name):
                errors.append(f"{field_name} mismatch")
        if self.request.expected_version_fragment not in receipt.version_output:
            errors.append("toolchain version mismatch")
        if receipt.command != self.request.command:
            errors.append("command mismatch")
        for digest_name in ("project_sha256", "source_sha256", "executable_sha256", "stdout_sha256", "stderr_sha256", "environment_digest"):
            value = getattr(receipt, digest_name)
            if len(value) != 64:
                errors.append(f"invalid {digest_name}")
        if receipt.verdict == ReceiptVerdict.ACCEPTED and receipt.returncode != 0:
            errors.append("accepted receipt has nonzero return code")
        if receipt.verdict == ReceiptVerdict.REJECTED and receipt.returncode == 0:
            errors.append("rejected receipt has zero return code")
        if runner.signature_profile == ReceiptSignatureProfile.LOCAL_REFERENCE_HMAC:
            secret = self._secrets.get(runner.runner_id)
            if not receipt.signature or not secret or not hmac_verify(receipt.signing_payload(), receipt.signature, secret):
                errors.append("local receipt signature mismatch")
        elif not receipt.signature:
            errors.append("missing external signature material")
        # External signature cryptography is delegated to a production adapter;
        # the core refuses promotion unless external profiles and independence are present.
        return not errors, errors

    def submit(self, receipt: KernelReceipt) -> None:
        if not receipt.signature and receipt.signature_profile == ReceiptSignatureProfile.LOCAL_REFERENCE_HMAC:
            self.sign_local(receipt)
        ok, errors = self.verify(receipt)
        if not ok:
            raise ValueError("; ".join(errors))
        self.receipts[receipt.receipt_id] = receipt

    def evaluate(self, policy: KernelQuorumPolicy | None = None) -> KernelQuorumDecision:
        policy = policy or KernelQuorumPolicy(required_toolchain=self.request.toolchain, expected_version_fragment=self.request.expected_version_fragment)
        if not self.receipts:
            return self._decision(KernelQuorumStatus.NO_RECEIPTS, ["No kernel receipts submitted"], {}, [])
        valid: list[KernelReceipt] = []
        invalid: dict[str, list[str]] = {}
        for receipt in self.receipts.values():
            ok, errors = self.verify(receipt)
            if ok:
                valid.append(receipt)
            else:
                invalid[receipt.receipt_id] = errors
        if not valid:
            return self._decision(KernelQuorumStatus.INVALID_RECEIPTS, ["No valid kernel receipts"], invalid, [])
        accepted = [r for r in valid if r.verdict == ReceiptVerdict.ACCEPTED]
        rejected = [r for r in valid if r.verdict == ReceiptVerdict.REJECTED]
        if accepted and rejected and policy.require_no_rejections:
            return self._decision(KernelQuorumStatus.CONFLICT, ["Accepted and rejected kernel receipts conflict"], invalid, valid)
        orgs = {r.organization_id for r in accepted}
        groups = {r.provenance_group for r in accepted}
        platforms = {r.platform_family for r in accepted}
        reasons: list[str] = []
        if len(orgs) < policy.minimum_organizations:
            reasons.append(f"organization quorum not met: {len(orgs)}/{policy.minimum_organizations}")
        if len(groups) < policy.minimum_independent_groups:
            reasons.append(f"independent provenance quorum not met: {len(groups)}/{policy.minimum_independent_groups}")
        if len(platforms) < policy.minimum_platform_families:
            reasons.append(f"platform quorum not met: {len(platforms)}/{policy.minimum_platform_families}")
        external_profiles = all(r.signature_profile != ReceiptSignatureProfile.LOCAL_REFERENCE_HMAC for r in accepted)
        external_independence = bool(accepted) and all(r.external_independence for r in accepted)
        if reasons:
            return self._decision(KernelQuorumStatus.INSUFFICIENT_QUORUM, reasons, invalid, valid)
        if policy.require_external_signatures_for_promotion and (not external_profiles or not external_independence):
            return self._decision(
                KernelQuorumStatus.LOCAL_PROCESS_QUORUM,
                ["Quorum mechanics passed, but external signatures or institutional independence are absent"],
                invalid,
                valid,
            )
        return self._decision(
            KernelQuorumStatus.FEDERATED_KERNEL_REPRODUCED,
            ["Independent signed kernel-receipt quorum satisfied"],
            invalid,
            valid,
        )

    def _decision(self, status: KernelQuorumStatus, reasons: list[str], invalid: dict[str, list[str]], valid: list[KernelReceipt]) -> KernelQuorumDecision:
        accepted = [r for r in valid if r.verdict == ReceiptVerdict.ACCEPTED]
        rejected = [r for r in valid if r.verdict == ReceiptVerdict.REJECTED]
        external = status == KernelQuorumStatus.FEDERATED_KERNEL_REPRODUCED
        theorem_status = "KERNEL_RECEIPT_QUORUM_REPRODUCED" if external else "KERNEL_RECEIPT_QUORUM_PENDING_EXTERNAL"
        return KernelQuorumDecision(
            request_id=self.request.request_id,
            status=status,
            reasons=reasons,
            valid_receipts=[r.receipt_id for r in valid],
            invalid_receipts=invalid,
            organizations=sorted({r.organization_id for r in accepted}),
            provenance_groups=sorted({r.provenance_group for r in accepted}),
            platform_families=sorted({r.platform_family for r in accepted}),
            accepted_receipts=[r.receipt_id for r in accepted],
            rejected_receipts=[r.receipt_id for r in rejected],
            external_independence_claimed=external,
            theorem_status=theorem_status,
        )


def build_receipt_request(*, project_dir: str | Path, theorem: str, toolchain: str, version_fragment: str) -> KernelReceiptRequest:
    project = Path(project_dir)
    source = project / "NexusUKernelBridge" / "AllSensitive.lean"
    files = {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(project.rglob("*")) if p.is_file() and p.name != "replay-manifest.json"}
    return KernelReceiptRequest(
        request_id=str(uuid.uuid4()),
        project_id="nexus-u-decision-tree-kernel-bridge",
        theorem="allSensitive_forces_allQueried",
        project_sha256=canonical_digest(files),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        toolchain=toolchain,
        expected_version_fragment=version_fragment,
        command=["lake", "build"],
    )


def make_reference_receipt(request: KernelReceiptRequest, runner: KernelRunnerIdentity, *, accepted: bool = True, salt: str = "") -> KernelReceipt:
    verdict = ReceiptVerdict.ACCEPTED if accepted else ReceiptVerdict.REJECTED
    return KernelReceipt(
        request_id=request.request_id,
        runner_id=runner.runner_id,
        organization_id=runner.organization_id,
        provenance_group=runner.provenance_group,
        key_id=runner.key_id,
        signature_profile=runner.signature_profile,
        project_id=request.project_id,
        theorem=request.theorem,
        project_sha256=request.project_sha256,
        source_sha256=request.source_sha256,
        toolchain=request.toolchain,
        version_output=f"Lean (version {request.expected_version_fragment}, reference-runner)",
        executable_sha256=hashlib.sha256(f"lean:{runner.runner_id}:{salt}".encode()).hexdigest(),
        command=list(request.command),
        returncode=0 if accepted else 1,
        stdout_sha256=hashlib.sha256(f"stdout:{runner.runner_id}:{accepted}:{salt}".encode()).hexdigest(),
        stderr_sha256=hashlib.sha256(f"stderr:{runner.runner_id}:{accepted}:{salt}".encode()).hexdigest(),
        verdict=verdict,
        platform_family=runner.platform_family,
        environment_digest=hashlib.sha256(f"env:{runner.runner_id}:{runner.platform_family}:{salt}".encode()).hexdigest(),
        external_independence=runner.external_independence,
    )
