from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Any

from .models import ArtifactRecord, StageEvent


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


class AuditChain:
    def __init__(self) -> None:
        self._head = "0" * 64
        self.entries: list[dict[str, Any]] = []

    @property
    def head(self) -> str:
        return self._head

    def append(self, event: StageEvent) -> str:
        body = asdict(event)
        digest = hashlib.sha256(self._head.encode() + canonical_json(body)).hexdigest()
        self.entries.append({"previous": self._head, "digest": digest, "event": body})
        self._head = digest
        return digest

    def verify(self) -> bool:
        head = "0" * 64
        for entry in self.entries:
            expected = hashlib.sha256(head.encode() + canonical_json(entry["event"])).hexdigest()
            if entry["previous"] != head or entry["digest"] != expected:
                return False
            head = expected
        return head == self._head

    def write(self, path: Path) -> None:
        path.write_text(json.dumps({"head": self._head, "entries": self.entries}, indent=2), encoding="utf-8")


def write_artifact(record: ArtifactRecord, output_dir: Path, chain: AuditChain) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    record.audit_root = chain.head
    artifact_path = output_dir / f"{record.artifact_id}.json"
    artifact_path.write_text(json.dumps(record.to_dict(), indent=2, default=str), encoding="utf-8")
    chain.write(output_dir / f"{record.artifact_id}.audit.json")
    return artifact_path
