from __future__ import annotations

from dataclasses import asdict, dataclass
import platform
import shutil
import subprocess
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Capability:
    name: str
    available: bool
    executable: str | None
    version: str | None
    role: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_TOOL_SPECS: tuple[tuple[str, tuple[str, ...], tuple[str, ...], str], ...] = (
    ("lean", ("lean",), ("--version",), "Lean kernel-facing formal proof adapter"),
    ("lake", ("lake",), ("--version",), "Lean project and dependency build tool"),
    ("dafny", ("dafny",), ("--version",), "Specification-aware program verifier"),
    ("git", ("git",), ("--version",), "Source provenance and revision identity"),
    ("docker", ("docker",), ("--version",), "Container build and execution boundary"),
    ("cosign", ("cosign",), ("version",), "Optional artifact and attestation signing"),
    ("kubectl", ("kubectl",), ("version", "--client"), "Kubernetes rollout control"),
)


def _version(executable: str, args: Iterable[str]) -> str | None:
    try:
        proc = subprocess.run(
            [executable, *args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = (proc.stdout or proc.stderr).strip()
    return text.splitlines()[0][:300] if text else None


def capability_report() -> dict[str, object]:
    tools: list[Capability] = []
    for name, candidates, args, role in _TOOL_SPECS:
        executable = next((shutil.which(item) for item in candidates if shutil.which(item)), None)
        tools.append(
            Capability(
                name=name,
                available=executable is not None,
                executable=executable,
                version=_version(executable, args) if executable else None,
                role=role,
            )
        )
    return {
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "tools": [item.to_dict() for item in tools],
        "internal": {
            "obligation_graph": True,
            "obligation_router": True,
            "federated_evidence": True,
            "cross_repository_graphs": True,
            "conflict_and_veto_policies": True,
        "tension_driven_discovery": True,
        "discriminating_experiment_design": True,
        "blind_discovery_trials": True,
        "corpus_provenance_hashing": True,
        "false_discovery_controls": True,
        "preregistered_reproduction": True,
        "process_isolated_evaluators": True,
        "third_party_replay_bundles": True,
        "lower_bound_discovery_lab": True,
        "machine_model_ledger": True,
        "reduction_graph": True,
        "proof_promotion_firewall": True,
        "active_lower_bound_search": True,
        "restricted_lower_bound_certificates": True,
        "adversarial_proof_route_attacks": True,
        "formalized_lower_bound_search": True,
        "specialized_decision_tree_checker": True,
        "proof_assistant_target_generation": True,
        "transposition_formalization_dag": True,
        },
    }
