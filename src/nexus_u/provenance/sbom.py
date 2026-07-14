from __future__ import annotations

from datetime import datetime, timezone
from importlib import metadata
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_cyclonedx_sbom(subject: Path | str | None = None) -> dict[str, Any]:
    components = []
    for dist in sorted(metadata.distributions(), key=lambda item: (item.metadata.get("Name") or "").lower()):
        name = dist.metadata.get("Name")
        if not name:
            continue
        components.append({
            "type": "library",
            "name": name,
            "version": dist.version,
            "purl": f"pkg:pypi/{name.lower().replace('_', '-')}@{dist.version}",
        })
    metadata_block: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tools": {"components": [{"type": "application", "name": "nexus-u", "version": "1.2.0"}]},
    }
    if subject is not None:
        path = Path(subject)
        if path.is_file():
            metadata_block["component"] = {
                "type": "application",
                "name": path.name,
                "hashes": [{"alg": "SHA-256", "content": _sha256(path)}],
            }
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:" + __import__("uuid").uuid4().hex,
        "version": 1,
        "metadata": metadata_block,
        "components": components,
    }


def write_sbom(sbom: dict[str, Any], path: Path | str) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(sbom, indent=2, sort_keys=True), encoding="utf-8")
    return output
