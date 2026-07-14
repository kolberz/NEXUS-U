from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from nexus_u.security.signing import write_signed_envelope
from .attestation import build_provenance_statement
from .sbom import build_cyclonedx_sbom


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_evidence_bundle(
    artifact_path: Path | str,
    *,
    audit_path: Path | str | None = None,
    obligation_graph_path: Path | str | None = None,
    policy_decisions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    artifact = Path(artifact_path)
    bundle: dict[str, Any] = {
        "bundle_type": "https://nexus-u.dev/evidence-bundle/v1",
        "artifact": {"path": artifact.name, "sha256": _sha256(artifact)},
        "provenance": build_provenance_statement(artifact),
        "sbom": build_cyclonedx_sbom(artifact),
        "policy_decisions": policy_decisions or [],
    }
    if audit_path:
        audit = Path(audit_path)
        if audit.is_file():
            bundle["audit"] = {"path": audit.name, "sha256": _sha256(audit)}
    if obligation_graph_path:
        graph = Path(obligation_graph_path)
        if graph.is_file():
            bundle["obligation_graph"] = {"path": graph.name, "sha256": _sha256(graph)}
    return bundle


def write_evidence_bundle(
    bundle: dict[str, Any],
    path: Path | str,
    *,
    secret: str | None = None,
    key_id: str = "local-hmac",
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if secret:
        return write_signed_envelope(bundle, output, key_id=key_id, secret=secret)
    output.write_text(json.dumps(bundle, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return output
