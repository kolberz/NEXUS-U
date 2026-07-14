from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid
from typing import Any

IN_TOTO_STATEMENT_V1 = "https://in-toto.io/Statement/v1"
SLSA_PROVENANCE_V1 = "https://slsa.dev/provenance/v1"
NEXUS_BUILD_TYPE = "https://nexus-u.dev/build/v1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_provenance_statement(
    subject_path: Path | str,
    *,
    builder_id: str = "https://nexus-u.dev/local-builder/v1",
    invocation_id: str | None = None,
    external_parameters: dict[str, Any] | None = None,
    resolved_dependencies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    path = Path(subject_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    now = _timestamp()
    return {
        "_type": IN_TOTO_STATEMENT_V1,
        "subject": [{"name": path.name, "digest": {"sha256": _sha256_file(path)}}],
        "predicateType": SLSA_PROVENANCE_V1,
        "predicate": {
            "buildDefinition": {
                "buildType": NEXUS_BUILD_TYPE,
                "externalParameters": external_parameters or {},
                "internalParameters": {},
                "resolvedDependencies": resolved_dependencies or [],
            },
            "runDetails": {
                "builder": {"id": builder_id},
                "metadata": {
                    "invocationId": invocation_id or str(uuid.uuid4()),
                    "startedOn": now,
                    "finishedOn": now,
                },
                "byproducts": [],
            },
        },
    }


def verify_provenance_statement(statement: dict[str, Any], subject_path: Path | str) -> tuple[bool, list[str]]:
    path = Path(subject_path)
    errors: list[str] = []
    if statement.get("_type") != IN_TOTO_STATEMENT_V1:
        errors.append("Unsupported in-toto Statement type")
    if statement.get("predicateType") != SLSA_PROVENANCE_V1:
        errors.append("Unsupported SLSA predicate type")
    subjects = statement.get("subject")
    if not isinstance(subjects, list) or not subjects:
        errors.append("Statement has no subjects")
    elif not path.is_file():
        errors.append("Subject file does not exist")
    else:
        expected = _sha256_file(path)
        matching = [item for item in subjects if item.get("name") == path.name]
        if not matching:
            errors.append("Subject name not present in statement")
        elif matching[0].get("digest", {}).get("sha256") != expected:
            errors.append("Subject digest mismatch")
    predicate = statement.get("predicate", {})
    if not predicate.get("runDetails", {}).get("builder", {}).get("id"):
        errors.append("Builder identity missing")
    return not errors, errors


def write_statement(statement: dict[str, Any], path: Path | str) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(statement, indent=2, sort_keys=True), encoding="utf-8")
    return output
