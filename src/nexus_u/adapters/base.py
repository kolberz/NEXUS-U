from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from nexus_u.core.models import Evidence, TaskSpec


@dataclass(slots=True)
class AdapterDescriptor:
    name: str
    version: str = "1"
    trust_level: str = "third_party"
    artifact_types: list[str] = field(default_factory=list)
    evidence_kinds: list[str] = field(default_factory=list)
    external_tools: list[str] = field(default_factory=list)
    sandboxed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "trust_level": self.trust_level,
            "artifact_types": list(self.artifact_types),
            "evidence_kinds": list(self.evidence_kinds),
            "external_tools": list(self.external_tools),
            "sandboxed": self.sandboxed,
        }


@dataclass(slots=True)
class AdapterResult:
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    obligations: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)


class Adapter(Protocol):
    name: str

    def construct(self, task: TaskSpec) -> AdapterResult: ...
    def execute(self, task: TaskSpec, constructed: AdapterResult) -> AdapterResult: ...
    def verify(self, task: TaskSpec, executed: AdapterResult) -> AdapterResult: ...
