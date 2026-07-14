from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Iterable
import uuid

from .models import Evidence, TaskSpec


class ObligationKind(StrEnum):
    INTENT = "INTENT"
    SPECIFICATION = "SPECIFICATION"
    REQUIREMENT = "REQUIREMENT"
    ASSUMPTION = "ASSUMPTION"
    CLAIM = "CLAIM"
    TEST = "TEST"
    PROOF = "PROOF"
    SAFETY = "SAFETY"
    POLICY = "POLICY"
    RESOURCE = "RESOURCE"
    RISK = "RISK"
    PROVENANCE = "PROVENANCE"
    EVIDENCE = "EVIDENCE"
    UNKNOWN = "UNKNOWN"


class ObligationStatus(StrEnum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    DISCHARGED = "DISCHARGED"
    DEFERRED = "DEFERRED"
    REFUTED = "REFUTED"
    ESCALATED = "ESCALATED"
    TRANSFERRED = "TRANSFERRED"


class Severity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Relation(StrEnum):
    DEPENDS_ON = "DEPENDS_ON"
    DISCHARGES = "DISCHARGES"
    INTRODUCES = "INTRODUCES"
    REFINES = "REFINES"
    DECOMPOSES = "DECOMPOSES"
    TRANSFERS = "TRANSFERS"
    VERIFIES = "VERIFIES"
    CONTRADICTS = "CONTRADICTS"
    BLOCKS = "BLOCKS"
    SUPPORTS = "SUPPORTS"


SEVERITY_WEIGHT = {
    Severity.INFO: 0.25,
    Severity.LOW: 1.0,
    Severity.MEDIUM: 3.0,
    Severity.HIGH: 8.0,
    Severity.CRITICAL: 20.0,
}

STATUS_FACTOR = {
    ObligationStatus.OPEN: 1.0,
    ObligationStatus.ACKNOWLEDGED: 0.2,
    ObligationStatus.DISCHARGED: 0.0,
    ObligationStatus.DEFERRED: 0.8,
    ObligationStatus.REFUTED: 0.0,
    ObligationStatus.ESCALATED: 1.2,
    ObligationStatus.TRANSFERRED: 0.1,
}


@dataclass(slots=True)
class ObligationNode:
    statement: str
    kind: ObligationKind = ObligationKind.UNKNOWN
    status: ObligationStatus = ObligationStatus.OPEN
    severity: Severity = Severity.MEDIUM
    blocking: bool = True
    source: str = "runtime"
    metadata: dict[str, Any] = field(default_factory=dict)
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ObligationEdge:
    source: str
    target: str
    relation: Relation
    metadata: dict[str, Any] = field(default_factory=dict)
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GraphEvent:
    operation: str
    affected: list[str]
    details: dict[str, Any] = field(default_factory=dict)
    active_before: list[str] = field(default_factory=list)
    active_after: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ObligationGraphError(ValueError):
    pass


class ObligationGraph:
    """Immutable-node obligation graph with accountable status transitions.

    Nodes are never deleted. Progress occurs only by changing their status or by
    introducing explicitly related nodes. This makes silent obligation loss
    structurally impossible and permits conservation auditing.
    """

    def __init__(self, graph_id: str | None = None) -> None:
        self.graph_id = graph_id or str(uuid.uuid4())
        self.nodes: dict[str, ObligationNode] = {}
        self.edges: dict[str, ObligationEdge] = {}
        self.events: list[GraphEvent] = []
        self.created_at = time.time()

    @classmethod
    def from_task(cls, task: TaskSpec) -> "ObligationGraph":
        graph = cls(graph_id=f"task:{task.task_id}")
        intent_id = graph.add_node(
            task.intent,
            kind=ObligationKind.INTENT,
            severity=Severity.HIGH,
            source="task.intent",
            metadata={"task_id": task.task_id},
        )
        for statement in task.assumptions:
            assumption_id = graph.add_node(
                statement,
                kind=ObligationKind.ASSUMPTION,
                status=ObligationStatus.ACKNOWLEDGED,
                severity=Severity.MEDIUM,
                blocking=False,
                source="task.assumptions",
            )
            graph.add_edge(assumption_id, intent_id, Relation.SUPPORTS)
        for condition in task.success_conditions:
            requirement_id = graph.add_node(
                condition,
                kind=ObligationKind.REQUIREMENT,
                severity=Severity.HIGH,
                source="task.success_conditions",
                metadata={"required_for": "release"},
            )
            graph.add_edge(requirement_id, intent_id, Relation.REFINES)
        for shortcut in task.prohibited_shortcuts:
            policy_id = graph.add_node(
                f"Prohibited shortcut must not appear: {shortcut}",
                kind=ObligationKind.POLICY,
                status=ObligationStatus.ACKNOWLEDGED,
                severity=Severity.HIGH,
                blocking=False,
                source="task.prohibited_shortcuts",
                metadata={"shortcut": shortcut},
            )
            graph.add_edge(policy_id, intent_id, Relation.BLOCKS)
        for raw in task.initial_obligations:
            if not isinstance(raw, dict) or not raw.get("statement"):
                continue
            graph.add_node(
                str(raw["statement"]),
                kind=ObligationKind(str(raw.get("kind", ObligationKind.UNKNOWN))),
                status=ObligationStatus(str(raw.get("status", ObligationStatus.OPEN))),
                severity=Severity(str(raw.get("severity", Severity.MEDIUM))),
                blocking=bool(raw.get("blocking", True)),
                source=str(raw.get("source", "task.initial_obligations")),
                metadata=dict(raw.get("metadata", {})),
            )
        graph.checkpoint("task_initialized", details={"task_id": task.task_id})
        return graph

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ObligationGraph":
        graph = cls(graph_id=raw.get("graph_id"))
        graph.created_at = float(raw.get("created_at", time.time()))
        for item in raw.get("nodes", []):
            node = ObligationNode(
                statement=item["statement"],
                kind=ObligationKind(item.get("kind", ObligationKind.UNKNOWN)),
                status=ObligationStatus(item.get("status", ObligationStatus.OPEN)),
                severity=Severity(item.get("severity", Severity.MEDIUM)),
                blocking=bool(item.get("blocking", True)),
                source=item.get("source", "runtime"),
                metadata=dict(item.get("metadata", {})),
                node_id=item["node_id"],
                created_at=float(item.get("created_at", time.time())),
                updated_at=float(item.get("updated_at", time.time())),
            )
            graph.nodes[node.node_id] = node
        for item in raw.get("edges", []):
            edge = ObligationEdge(
                source=item["source"],
                target=item["target"],
                relation=Relation(item["relation"]),
                metadata=dict(item.get("metadata", {})),
                edge_id=item["edge_id"],
                created_at=float(item.get("created_at", time.time())),
            )
            graph.edges[edge.edge_id] = edge
        for item in raw.get("events", []):
            graph.events.append(
                GraphEvent(
                    operation=item["operation"],
                    affected=list(item.get("affected", [])),
                    details=dict(item.get("details", {})),
                    active_before=list(item.get("active_before", [])),
                    active_after=list(item.get("active_after", [])),
                    timestamp=float(item.get("timestamp", time.time())),
                )
            )
        return graph

    def _active_ids(self) -> list[str]:
        return sorted(
            node.node_id
            for node in self.nodes.values()
            if node.kind != ObligationKind.EVIDENCE
            and node.status in {ObligationStatus.OPEN, ObligationStatus.DEFERRED, ObligationStatus.ESCALATED}
        )

    def add_node(
        self,
        statement: str,
        *,
        kind: ObligationKind = ObligationKind.UNKNOWN,
        status: ObligationStatus = ObligationStatus.OPEN,
        severity: Severity = Severity.MEDIUM,
        blocking: bool = True,
        source: str = "runtime",
        metadata: dict[str, Any] | None = None,
        node_id: str | None = None,
    ) -> str:
        if not statement.strip():
            raise ObligationGraphError("Obligation statement cannot be empty")
        before = self._active_ids()
        node = ObligationNode(
            statement=statement.strip(),
            kind=kind,
            status=status,
            severity=severity,
            blocking=blocking,
            source=source,
            metadata=metadata or {},
            node_id=node_id or str(uuid.uuid4()),
        )
        if node.node_id in self.nodes:
            raise ObligationGraphError(f"Duplicate node_id: {node.node_id}")
        self.nodes[node.node_id] = node
        self._record("CREATE_OBLIGATION" if kind != ObligationKind.EVIDENCE else "ADD_EVIDENCE", [node.node_id], before=before)
        return node.node_id

    def add_evidence(self, evidence: Evidence | dict[str, Any], *, source: str = "verification") -> str:
        raw = asdict(evidence) if isinstance(evidence, Evidence) else dict(evidence)
        statement = raw.get("summary") or raw.get("statement") or raw.get("kind") or "Evidence"
        return self.add_node(
            str(statement),
            kind=ObligationKind.EVIDENCE,
            status=ObligationStatus.DISCHARGED,
            severity=Severity.INFO,
            blocking=False,
            source=source,
            metadata=raw,
        )

    def add_edge(
        self,
        source: str,
        target: str,
        relation: Relation,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        if source not in self.nodes or target not in self.nodes:
            raise ObligationGraphError("Edge endpoints must exist")
        edge = ObligationEdge(source=source, target=target, relation=relation, metadata=metadata or {})
        self.edges[edge.edge_id] = edge
        cycles = self.cycles()
        if cycles and relation not in {Relation.CONTRADICTS}:
            del self.edges[edge.edge_id]
            raise ObligationGraphError(f"Edge would introduce cycle: {cycles[0]}")
        self._record("ADD_RELATION", [source, target], details={"relation": relation, "edge_id": edge.edge_id})
        return edge.edge_id

    def find(self, *, kind: ObligationKind | None = None, status: ObligationStatus | None = None, source: str | None = None) -> list[ObligationNode]:
        result = list(self.nodes.values())
        if kind is not None:
            result = [node for node in result if node.kind == kind]
        if status is not None:
            result = [node for node in result if node.status == status]
        if source is not None:
            result = [node for node in result if node.source == source]
        return result

    def discharge(self, node_id: str, evidence_ids: Iterable[str], *, reason: str = "") -> None:
        node = self._node(node_id)
        evidence_ids = list(evidence_ids)
        if node.kind == ObligationKind.EVIDENCE:
            raise ObligationGraphError("Evidence nodes cannot be discharged as obligations")
        if not evidence_ids:
            raise ObligationGraphError("Discharge requires evidence")
        for evidence_id in evidence_ids:
            evidence = self._node(evidence_id)
            if evidence.kind != ObligationKind.EVIDENCE:
                raise ObligationGraphError(f"Node {evidence_id} is not evidence")
        before = self._active_ids()
        for evidence_id in evidence_ids:
            self.add_edge(evidence_id, node_id, Relation.DISCHARGES, metadata={"reason": reason})
        node.status = ObligationStatus.DISCHARGED
        node.updated_at = time.time()
        node.metadata["discharge_reason"] = reason
        self._record("DISCHARGE_OBLIGATION", [node_id, *evidence_ids], before=before, details={"reason": reason})

    def defer(self, node_id: str, *, reason: str, retry_conditions: list[str] | None = None) -> None:
        node = self._node(node_id)
        before = self._active_ids()
        node.status = ObligationStatus.DEFERRED
        node.updated_at = time.time()
        node.metadata["defer_reason"] = reason
        node.metadata["retry_conditions"] = retry_conditions or []
        self._record("DEFER_OBLIGATION", [node_id], before=before, details={"reason": reason})

    def escalate(self, node_id: str, *, reason: str, owner: str | None = None) -> None:
        node = self._node(node_id)
        before = self._active_ids()
        node.status = ObligationStatus.ESCALATED
        node.updated_at = time.time()
        node.metadata["escalation_reason"] = reason
        if owner:
            node.metadata["owner"] = owner
        self._record("ESCALATE_OBLIGATION", [node_id], before=before, details={"reason": reason, "owner": owner})

    def refute(self, node_id: str, evidence_ids: Iterable[str], *, reason: str = "") -> None:
        node = self._node(node_id)
        evidence_ids = list(evidence_ids)
        if not evidence_ids:
            raise ObligationGraphError("Refutation requires counterevidence")
        before = self._active_ids()
        for evidence_id in evidence_ids:
            evidence = self._node(evidence_id)
            if evidence.kind != ObligationKind.EVIDENCE:
                raise ObligationGraphError("Refutation support must be evidence")
            self.add_edge(evidence_id, node_id, Relation.CONTRADICTS, metadata={"reason": reason})
        node.status = ObligationStatus.REFUTED
        node.updated_at = time.time()
        node.metadata["refutation_reason"] = reason
        self._record("REFUTE_OBLIGATION", [node_id, *evidence_ids], before=before, details={"reason": reason})

    def transfer(self, node_id: str, new_statement: str, *, relation: Relation = Relation.REFINES, reason: str = "") -> str:
        old = self._node(node_id)
        before = self._active_ids()
        new_id = self.add_node(
            new_statement,
            kind=old.kind,
            severity=old.severity,
            blocking=old.blocking,
            source="shape_transform",
            metadata={"transferred_from": node_id, "reason": reason},
        )
        self.add_edge(new_id, node_id, relation, metadata={"reason": reason})
        old.status = ObligationStatus.TRANSFERRED
        old.updated_at = time.time()
        self._record("TRANSFER_OBLIGATION", [node_id, new_id], before=before, details={"reason": reason, "relation": relation})
        return new_id

    def checkpoint(self, operation: str, *, details: dict[str, Any] | None = None) -> None:
        active = self._active_ids()
        self.events.append(GraphEvent(operation=operation, affected=[], details=details or {}, active_before=active, active_after=active))

    def _record(
        self,
        operation: str,
        affected: list[str],
        *,
        before: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            GraphEvent(
                operation=operation,
                affected=affected,
                details=details or {},
                active_before=before if before is not None else self._active_ids(),
                active_after=self._active_ids(),
            )
        )

    def _node(self, node_id: str) -> ObligationNode:
        try:
            return self.nodes[node_id]
        except KeyError as exc:
            raise ObligationGraphError(f"Unknown node: {node_id}") from exc

    def cycles(self) -> list[list[str]]:
        adjacency: dict[str, list[str]] = {node_id: [] for node_id in self.nodes}
        for edge in self.edges.values():
            if edge.relation == Relation.CONTRADICTS:
                continue
            adjacency[edge.source].append(edge.target)
        visiting: set[str] = set()
        visited: set[str] = set()
        stack: list[str] = []
        found: list[list[str]] = []

        def visit(node_id: str) -> None:
            if node_id in visiting:
                idx = stack.index(node_id)
                found.append(stack[idx:] + [node_id])
                return
            if node_id in visited:
                return
            visiting.add(node_id)
            stack.append(node_id)
            for nxt in adjacency[node_id]:
                visit(nxt)
            stack.pop()
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in adjacency:
            visit(node_id)
        return found

    def evidence_for(self, node_id: str) -> list[ObligationNode]:
        evidence_ids = [
            edge.source
            for edge in self.edges.values()
            if edge.target == node_id and edge.relation in {Relation.DISCHARGES, Relation.VERIFIES, Relation.SUPPORTS, Relation.CONTRADICTS}
        ]
        return [self.nodes[item] for item in evidence_ids if item in self.nodes and self.nodes[item].kind == ObligationKind.EVIDENCE]

    def verify_conservation(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        node_ids = set(self.nodes)
        for edge in self.edges.values():
            if edge.source not in node_ids or edge.target not in node_ids:
                errors.append(f"Dangling edge {edge.edge_id}")
        for node in self.nodes.values():
            if node.kind == ObligationKind.EVIDENCE:
                continue
            if node.status in {ObligationStatus.DISCHARGED, ObligationStatus.REFUTED} and not self.evidence_for(node.node_id):
                errors.append(f"Terminal obligation lacks evidence: {node.node_id}")
            if node.status == ObligationStatus.DEFERRED and not node.metadata.get("defer_reason"):
                errors.append(f"Deferred obligation lacks reason: {node.node_id}")
            if node.status == ObligationStatus.ESCALATED and not node.metadata.get("escalation_reason"):
                errors.append(f"Escalated obligation lacks reason: {node.node_id}")
            if node.status == ObligationStatus.TRANSFERRED:
                related = [edge for edge in self.edges.values() if edge.target == node.node_id and edge.relation in {Relation.REFINES, Relation.TRANSFERS, Relation.DECOMPOSES}]
                if not related:
                    errors.append(f"Transferred obligation lacks transport edge: {node.node_id}")
        errors.extend(f"Graph cycle detected: {' -> '.join(cycle)}" for cycle in self.cycles())
        previous_nodes: set[str] = set()
        for event in self.events:
            current = set(event.active_before) | set(event.active_after) | set(event.affected)
            if not current.issubset(node_ids):
                errors.append(f"Event references unknown node during {event.operation}")
            previous_nodes |= current
        if not previous_nodes.issubset(node_ids):
            errors.append("Historical obligation disappeared from graph")
        return not errors, errors

    def unresolved(self, *, blocking_only: bool = False) -> list[ObligationNode]:
        statuses = {ObligationStatus.OPEN, ObligationStatus.DEFERRED, ObligationStatus.ESCALATED}
        result = [node for node in self.nodes.values() if node.kind != ObligationKind.EVIDENCE and node.status in statuses]
        if blocking_only:
            result = [node for node in result if node.blocking]
        return result

    def epistemic_potential(self) -> float:
        return round(
            sum(SEVERITY_WEIGHT[node.severity] * STATUS_FACTOR[node.status] for node in self.nodes.values() if node.kind != ObligationKind.EVIDENCE),
            6,
        )

    def promotion_decision(self, target: str = "RELEASED") -> dict[str, Any]:
        valid, errors = self.verify_conservation()
        blockers = [
            node
            for node in self.unresolved(blocking_only=True)
            if node.severity in {Severity.HIGH, Severity.CRITICAL}
        ]
        evidence_count = len(self.find(kind=ObligationKind.EVIDENCE))
        required_kinds: dict[str, set[ObligationKind]] = {
            "RELEASED": {ObligationKind.INTENT, ObligationKind.REQUIREMENT, ObligationKind.CLAIM, ObligationKind.SAFETY, ObligationKind.POLICY},
            "KERNEL_VERIFIED": {ObligationKind.CLAIM, ObligationKind.PROOF},
        }
        missing_kinds: list[str] = []
        for kind in required_kinds.get(target, set()):
            nodes = self.find(kind=kind)
            if not nodes or any(node.blocking and node.status not in {ObligationStatus.DISCHARGED, ObligationStatus.ACKNOWLEDGED, ObligationStatus.REFUTED} for node in nodes):
                missing_kinds.append(str(kind))
        allowed = valid and not blockers and evidence_count > 0 and not missing_kinds
        return {
            "target": target,
            "allowed": allowed,
            "conservation_valid": valid,
            "errors": errors,
            "blocking_obligations": [node.to_dict() for node in blockers],
            "missing_kinds": missing_kinds,
            "evidence_count": evidence_count,
            "epistemic_potential": self.epistemic_potential(),
        }

    def summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        by_kind: dict[str, int] = {}
        for node in self.nodes.values():
            by_status[str(node.status)] = by_status.get(str(node.status), 0) + 1
            by_kind[str(node.kind)] = by_kind.get(str(node.kind), 0) + 1
        valid, errors = self.verify_conservation()
        return {
            "graph_id": self.graph_id,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "event_count": len(self.events),
            "by_status": by_status,
            "by_kind": by_kind,
            "unresolved_count": len(self.unresolved()),
            "blocking_unresolved_count": len(self.unresolved(blocking_only=True)),
            "epistemic_potential": self.epistemic_potential(),
            "conservation_valid": valid,
            "conservation_errors": errors,
            "sha256": self.sha256(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "https://nexus-u.dev/obligation-graph/v1",
            "graph_id": self.graph_id,
            "created_at": self.created_at,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges.values()],
            "events": [event.to_dict() for event in self.events],
            "summary": self.summary_without_hash(),
        }

    def summary_without_hash(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        by_kind: dict[str, int] = {}
        for node in self.nodes.values():
            by_status[str(node.status)] = by_status.get(str(node.status), 0) + 1
            by_kind[str(node.kind)] = by_kind.get(str(node.kind), 0) + 1
        valid, errors = self.verify_conservation()
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "event_count": len(self.events),
            "by_status": by_status,
            "by_kind": by_kind,
            "unresolved_count": len(self.unresolved()),
            "blocking_unresolved_count": len(self.unresolved(blocking_only=True)),
            "epistemic_potential": self.epistemic_potential(),
            "conservation_valid": valid,
            "conservation_errors": errors,
        }

    def sha256(self) -> str:
        canonical = json.dumps(
            {
                "graph_id": self.graph_id,
                "nodes": [node.to_dict() for node in sorted(self.nodes.values(), key=lambda item: item.node_id)],
                "edges": [edge.to_dict() for edge in sorted(self.edges.values(), key=lambda item: item.edge_id)],
                "events": [event.to_dict() for event in self.events],
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def write(self, path: Path | str) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.to_dict(), indent=2, default=str), encoding="utf-8")
        return output


def load_obligation_graph(path: Path | str) -> ObligationGraph:
    return ObligationGraph.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
