from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable

from nexus_u.adapters.registry import AdapterRegistry
from nexus_u.observability.metrics import METRICS
from nexus_u.orchestration.planner import build_workflow_plan
from nexus_u.provenance.bundle import build_evidence_bundle, write_evidence_bundle
from nexus_u.routing import ObligationRouter
from nexus_u.storage.sqlite import ControlStore
from .audit import AuditChain, write_artifact
from .claims import assign_status, strongest_evidence_status
from .models import ArtifactRecord, Claim, Evidence, RunStatus, StageEvent, TaskSpec
from .obligation_metrics import compute_obligation_metrics
from .obligation_graph import (
    ObligationGraph,
    ObligationKind,
    ObligationStatus,
    Relation,
    Severity,
)
from .policy import PolicyEngine
from .resources import BudgetExceeded, ResourceGuard
from .state_machine import ALLOWED, transition


class Pipeline:
    def __init__(
        self,
        output_dir: Path | str = "artifacts",
        registry: AdapterRegistry | None = None,
        *,
        policy_engine: PolicyEngine | None = None,
        store: ControlStore | None = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.registry = registry or AdapterRegistry()
        self.policy_engine = policy_engine or PolicyEngine()
        self.store = store

    def _advance(self, record: ArtifactRecord, chain: AuditChain, target: RunStatus, message: str, **metadata: Any) -> None:
        record.status = transition(record.status, target)
        event = StageEvent(stage=target, status="ok", message=message, metadata=metadata)
        record.events.append(event)
        chain.append(event)
        METRICS.event("pipeline_stage", artifact_id=record.artifact_id, stage=str(target), status="ok")

    def _terminal(self, record: ArtifactRecord, chain: AuditChain, target: RunStatus, message: str, **metadata: Any) -> None:
        record.status = transition(record.status, target)
        event = StageEvent(stage=target, status="terminal", message=message, metadata=metadata)
        record.events.append(event)
        chain.append(event)
        METRICS.event("pipeline_stage", artifact_id=record.artifact_id, stage=str(target), status="terminal")

    def _policy_event(self, record: ArtifactRecord, chain: AuditChain, decision: dict[str, Any]) -> None:
        record.policy_decisions.append(decision)
        event = StageEvent(
            stage=f"POLICY_{decision['phase'].upper()}",
            status="allow" if decision["allowed"] else "deny",
            message=f"Policy {decision['policy_id']} {'allowed' if decision['allowed'] else 'denied'} {decision['phase']}",
            metadata=decision,
        )
        record.events.append(event)
        chain.append(event)

    def _add_evidence(self, graph: ObligationGraph, evidence: Iterable[Evidence], source: str) -> list[str]:
        return [graph.add_evidence(item, source=source) for item in evidence]

    def _apply_obligation_results(
        self,
        graph: ObligationGraph,
        raw_results: Any,
        *,
        source: str,
    ) -> None:
        if not isinstance(raw_results, list):
            return
        for raw in raw_results:
            if not isinstance(raw, dict) or not raw.get("statement"):
                continue
            try:
                kind = ObligationKind(str(raw.get("kind", "REQUIREMENT")))
            except ValueError:
                kind = ObligationKind.REQUIREMENT
            try:
                severity = Severity(str(raw.get("severity", "HIGH")))
            except ValueError:
                severity = Severity.HIGH
            node_id = graph.add_node(
                str(raw["statement"]),
                kind=kind,
                severity=severity,
                blocking=bool(raw.get("blocking", True)),
                source=source,
                metadata={"external_result": True},
            )
            evidence_id = graph.add_evidence(
                {
                    "kind": "delivery_check",
                    "summary": str(raw.get("evidence_summary", raw["statement"])),
                    "success": bool(raw.get("success", False)),
                    "metadata": dict(raw.get("metadata", {})),
                },
                source=source,
            )
            if bool(raw.get("success", False)):
                graph.discharge(node_id, [evidence_id], reason="External delivery check passed")
            else:
                graph.refute(node_id, [evidence_id], reason="External delivery check failed")
                remediation = graph.add_node(
                    f"Remediate failed obligation: {raw['statement']}",
                    kind=kind,
                    severity=severity,
                    blocking=True,
                    source=source,
                )
                graph.defer(
                    remediation,
                    reason="Delivery check failed",
                    retry_conditions=["Correct the candidate", "Re-run the failed check"],
                )

    def _add_runtime_obligations(
        self,
        graph: ObligationGraph,
        obligations: Iterable[str],
        *,
        source: str,
        severity: Severity = Severity.HIGH,
        defer_reason: str | None = None,
    ) -> list[str]:
        ids: list[str] = []
        for statement in obligations:
            node_id = graph.add_node(
                str(statement),
                kind=ObligationKind.REQUIREMENT,
                severity=severity,
                source=source,
            )
            if defer_reason:
                graph.defer(node_id, reason=defer_reason)
            ids.append(node_id)
        return ids

    def _persist(self, record: ArtifactRecord, chain: AuditChain, graph: ObligationGraph) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        graph_path = self.output_dir / f"{record.artifact_id}.obligations.json"
        record.obligation_graph_path = graph_path.name
        record.obligation_graph = graph.to_dict()
        record.obligation_summary = graph.summary()
        record.obligation_metrics = compute_obligation_metrics(graph).to_dict()
        record.epistemic_potential = graph.epistemic_potential()
        router = ObligationRouter(self.store)
        record.routing_recommendations = [
            decision.to_dict() for decision in router.recommend_unresolved(graph, limit=25)
        ]
        if record.routing_recommendations:
            graph.checkpoint(
                "obligation_routes_recommended",
                details={"count": len(record.routing_recommendations), "policy": "obligation-router-v1"},
            )
            record.obligation_graph = graph.to_dict()
            record.obligation_summary = graph.summary()
            record.obligation_metrics = compute_obligation_metrics(graph).to_dict()
        graph.write(graph_path)
        record.audit_root = chain.head
        record.evidence_bundle = f"{record.artifact_id}.evidence.json"
        artifact_path = write_artifact(record, self.output_dir, chain)
        audit_path = self.output_dir / f"{record.artifact_id}.audit.json"
        bundle = build_evidence_bundle(
            artifact_path,
            audit_path=audit_path,
            obligation_graph_path=graph_path,
            policy_decisions=record.policy_decisions,
        )
        write_evidence_bundle(
            bundle,
            self.output_dir / record.evidence_bundle,
            secret=os.environ.get("NEXUS_U_SIGNING_KEY"),
            key_id=os.environ.get("NEXUS_U_SIGNING_KEY_ID", "local-hmac"),
        )
        if self.store is not None:
            self.store.index_artifact(record, artifact_path)
        METRICS.set_gauge("nexus_u_obligation_epistemic_potential", record.epistemic_potential)
        METRICS.set_gauge("nexus_u_obligation_unresolved", record.obligation_summary.get("unresolved_count", 0))
        return artifact_path

    def run(self, task: TaskSpec) -> tuple[ArtifactRecord, Path]:
        record = ArtifactRecord(task=task)
        chain = AuditChain()
        graph = ObligationGraph.from_task(task)
        guard = ResourceGuard(task.budget)
        METRICS.inc("nexus_u_pipeline_runs_total", adapter=task.adapter)
        METRICS.set_gauge("nexus_u_pipeline_active", 1)

        try:
            self._advance(record, chain, RunStatus.INTENT_COMPILED, "Intent compiled")
            self._advance(record, chain, RunStatus.ASSUMPTIONS_EXPOSED, "Assumptions recorded", count=len(task.assumptions))

            preflight_obligation = graph.add_node(
                "Task must satisfy preflight policy",
                kind=ObligationKind.POLICY,
                severity=Severity.HIGH,
                source="policy.preflight",
            )
            preflight = self.policy_engine.evaluate_preflight(task, self.registry.names())
            self._policy_event(record, chain, preflight.to_dict())
            preflight_evidence = graph.add_evidence(
                {"kind": "policy", "summary": f"Preflight decision: {'allow' if preflight.allowed else 'deny'}", "decision": preflight.to_dict()},
                source="policy.preflight",
            )
            if not preflight.allowed:
                graph.refute(preflight_obligation, [preflight_evidence], reason="Policy denied task")
                reasons = [*preflight.reasons, *(f"Required approval: {item}" for item in preflight.required_approvals)]
                record.unresolved_obligations.extend(reasons)
                self._add_runtime_obligations(graph, reasons, source="policy.preflight", defer_reason="Policy approval required")
                self._terminal(record, chain, RunStatus.REJECTED, "Policy preflight rejected task")
                return record, self._persist(record, chain, graph)
            graph.discharge(preflight_obligation, [preflight_evidence], reason="Preflight policy allowed task")

            workflow_plan = build_workflow_plan(task)
            spec_id = graph.add_node(
                f"Formalized target for {task.artifact_type}: {task.intent}",
                kind=ObligationKind.SPECIFICATION,
                status=ObligationStatus.ACKNOWLEDGED,
                severity=Severity.HIGH,
                blocking=False,
                source="orchestration.plan",
                metadata={"workflow_plan": workflow_plan},
            )
            intent_nodes = graph.find(kind=ObligationKind.INTENT)
            if intent_nodes:
                graph.add_edge(spec_id, intent_nodes[0].node_id, Relation.REFINES)
            execution_contract_id = graph.add_node(
                "Constructed artifact must execute and satisfy declared success conditions",
                kind=ObligationKind.REQUIREMENT,
                severity=Severity.HIGH,
                source="pipeline.execution_contract",
            )
            graph.add_edge(execution_contract_id, spec_id, Relation.DEPENDS_ON)
            self._advance(
                record,
                chain,
                RunStatus.TARGET_FORMALIZED,
                "Target normalized",
                modes=[str(m) for m in task.modes],
                workflow_plan=workflow_plan,
            )
            self._advance(record, chain, RunStatus.CANDIDATES_GENERATED, "Adapter selected", adapter=task.adapter)
            self._advance(record, chain, RunStatus.FALSIFICATION, "Preflight falsification completed")
            self._advance(record, chain, RunStatus.OBSTRUCTION_CLASSIFIED, "No blocking obstruction detected")
            self._advance(record, chain, RunStatus.STRATEGY_ROUTED, "Construction strategy routed")

            adapter = self.registry.get(task.adapter)
            constructed = adapter.construct(task)
            if not constructed.success:
                record.unresolved_obligations.extend(constructed.obligations)
                self._add_runtime_obligations(graph, constructed.obligations, source="adapter.construct", defer_reason="Construction failed")
                self._terminal(record, chain, RunStatus.REJECTED, "Construction failed")
                return record, self._persist(record, chain, graph)

            record.output = constructed.output
            construction_evidence = graph.add_evidence(
                {"kind": "construction", "summary": f"Adapter {task.adapter} constructed artifact", "logs": constructed.logs},
                source="adapter.construct",
            )
            graph.add_edge(construction_evidence, spec_id, Relation.SUPPORTS)
            self._advance(record, chain, RunStatus.ARTIFACT_CONSTRUCTED, "Artifact constructed")
            guard.enforce(len(str(record.output).encode()))

            executed = adapter.execute(task, constructed)
            record.output = executed.output
            execution_evidence_ids = self._add_evidence(graph, executed.evidence, "adapter.execute")
            self._apply_obligation_results(graph, executed.output.get("obligation_results"), source="adapter.obligation_results")
            if not executed.success:
                record.unresolved_obligations.extend(executed.obligations)
                self._add_runtime_obligations(graph, executed.obligations, source="adapter.execute", defer_reason="Execution incomplete")
                self._terminal(record, chain, RunStatus.PARTIAL, "Execution did not satisfy requirements")
                return record, self._persist(record, chain, graph)

            if not execution_evidence_ids:
                execution_evidence_ids.append(
                    graph.add_evidence(
                        {"kind": "execution", "summary": "Adapter reported successful execution", "adapter": task.adapter},
                        source="adapter.execute",
                    )
                )
            graph.discharge(execution_contract_id, execution_evidence_ids, reason="Execution adapter completed successfully")
            for requirement in graph.find(kind=ObligationKind.REQUIREMENT, source="task.success_conditions"):
                graph.discharge(requirement.node_id, execution_evidence_ids, reason="Adapter confirmed success condition")
            self._advance(record, chain, RunStatus.EXECUTED, "Artifact executed")
            guard.enforce(len(str(record.output).encode()))

            verified = adapter.verify(task, executed)
            record.output = verified.output
            record.unresolved_obligations.extend(verified.obligations)
            evidence_probe = Claim(statement="evidence probe", evidence=list(verified.evidence))
            base_claim = Claim(
                statement=f"Artifact {record.artifact_id} satisfies its declared execution contract",
                requested_status=strongest_evidence_status(evidence_probe),
                assumptions=list(task.assumptions),
                evidence=list(verified.evidence),
            )
            assign_status(base_claim)
            record.claims.append(base_claim)
            claim_id = graph.add_node(
                base_claim.statement,
                kind=ObligationKind.CLAIM,
                severity=Severity.HIGH,
                source="verification.base_claim",
                metadata={"assigned_status": str(base_claim.assigned_status), "requested_status": str(base_claim.requested_status)},
            )
            verification_evidence_ids = self._add_evidence(graph, verified.evidence, "adapter.verify")

            if not verified.success or not verification_evidence_ids:
                reasons = verified.obligations or ["Verification produced no acceptable evidence"]
                record.unresolved_obligations.extend(item for item in reasons if item not in record.unresolved_obligations)
                self._add_runtime_obligations(graph, reasons, source="adapter.verify", defer_reason="Verification incomplete")
                self._terminal(record, chain, RunStatus.PARTIAL, "Verification incomplete")
                return record, self._persist(record, chain, graph)

            graph.discharge(claim_id, verification_evidence_ids, reason=f"Evidence supports {base_claim.assigned_status}")
            proof_nodes = [node for node in graph.find(kind=ObligationKind.PROOF) if node.status == ObligationStatus.OPEN]
            if proof_nodes and str(base_claim.assigned_status) == "KERNEL_VERIFIED":
                for node in proof_nodes:
                    graph.discharge(node.node_id, verification_evidence_ids, reason="Kernel evidence accepted")
            self._advance(record, chain, RunStatus.VERIFIED, "Verification completed", claim_status=base_claim.assigned_status)

            release_policy_id = graph.add_node(
                "Artifact must satisfy release policy",
                kind=ObligationKind.POLICY,
                severity=Severity.HIGH,
                source="policy.release",
            )
            release_decision = self.policy_engine.evaluate_release(task, record)
            self._policy_event(record, chain, release_decision.to_dict())
            release_evidence = graph.add_evidence(
                {"kind": "policy", "summary": f"Release decision: {'allow' if release_decision.allowed else 'deny'}", "decision": release_decision.to_dict()},
                source="policy.release",
            )
            if not release_decision.allowed:
                graph.refute(release_policy_id, [release_evidence], reason="Release policy denied artifact")
                record.unresolved_obligations.extend(release_decision.reasons)
                self._add_runtime_obligations(graph, release_decision.reasons, source="policy.release", defer_reason="Release policy not satisfied")
                self._terminal(record, chain, RunStatus.REJECTED, "Policy release gate rejected artifact")
                return record, self._persist(record, chain, graph)
            graph.discharge(release_policy_id, [release_evidence], reason="Release policy allowed artifact")
            self._advance(record, chain, RunStatus.POLICY_REVIEWED, "Policy-as-code release gate passed", policy_id=release_decision.policy_id)

            safety_id = graph.add_node(
                "Artifact must pass scoped safety and feasibility review",
                kind=ObligationKind.SAFETY,
                severity=Severity.CRITICAL,
                source="assurance.safety",
            )
            safety_evidence = graph.add_evidence(
                {"kind": "safety", "summary": "Safety and feasibility gate evaluated", "forced_failure": bool(task.inputs.get("force_safety_failure", False))},
                source="assurance.safety",
            )
            if bool(task.inputs.get("force_safety_failure", False)):
                graph.refute(safety_id, [safety_evidence], reason="Safety gate forced to fail")
                record.unresolved_obligations.append("Safety gate forced to fail")
                self._add_runtime_obligations(graph, ["Resolve safety gate failure"], source="assurance.safety", severity=Severity.CRITICAL, defer_reason="Unsafe artifact")
                self._terminal(record, chain, RunStatus.REJECTED, "Safety gate rejected artifact")
                return record, self._persist(record, chain, graph)
            graph.discharge(safety_id, [safety_evidence], reason="Scoped safety review passed")
            self._advance(record, chain, RunStatus.SAFETY_REVIEWED, "Safety and feasibility review passed")

            if task.prohibited_shortcuts and any(shortcut.lower() in str(record.output).lower() for shortcut in task.prohibited_shortcuts):
                record.unresolved_obligations.append("Prohibited shortcut detected")
                self._add_runtime_obligations(graph, ["Remove prohibited shortcut"], source="assurance.adversarial", defer_reason="Theorem or artifact drift detected")
                self._terminal(record, chain, RunStatus.REJECTED, "Adversarial review rejected artifact")
                return record, self._persist(record, chain, graph)

            intent_evidence = graph.add_evidence(
                {"kind": "review", "summary": "Adversarial review found no intent or scope drift"},
                source="assurance.adversarial",
            )
            for intent in graph.find(kind=ObligationKind.INTENT, status=ObligationStatus.OPEN):
                graph.discharge(intent.node_id, [intent_evidence], reason="Intent preserved through released artifact")
            self._advance(record, chain, RunStatus.ADVERSARIAL_REVIEWED, "Adversarial review passed")

            provenance_id = graph.add_node(
                "Released artifact must preserve provenance and obligation history",
                kind=ObligationKind.PROVENANCE,
                severity=Severity.HIGH,
                source="assurance.provenance",
            )
            provenance_evidence = graph.add_evidence(
                {"kind": "provenance", "summary": "Audit chain and obligation graph prepared for persistence"},
                source="assurance.provenance",
            )
            graph.discharge(provenance_id, [provenance_evidence], reason="Provenance artifacts generated")

            promotion = graph.promotion_decision("RELEASED")
            promotion_event = StageEvent(
                stage="OBLIGATION_PROMOTION_GATE",
                status="allow" if promotion["allowed"] else "deny",
                message="Obligation promotion gate evaluated",
                metadata=promotion,
            )
            record.events.append(promotion_event)
            chain.append(promotion_event)
            if not promotion["allowed"]:
                for blocker in promotion["blocking_obligations"]:
                    statement = blocker["statement"]
                    if statement not in record.unresolved_obligations:
                        record.unresolved_obligations.append(statement)
                record.unresolved_obligations.extend(error for error in promotion["errors"] if error not in record.unresolved_obligations)
                self._terminal(record, chain, RunStatus.PARTIAL, "Obligation promotion gate blocked release")
                return record, self._persist(record, chain, graph)

            self._advance(record, chain, RunStatus.CERTIFIED, "Artifact certified relative to declared evidence")
            record.reproducible = True
            self._advance(record, chain, RunStatus.CURATED, "Artifact curated")
            record.released = True
            self._advance(record, chain, RunStatus.RELEASED, "Artifact released")
            graph.checkpoint("artifact_released", details={"artifact_id": record.artifact_id, "promotion": promotion})
            METRICS.inc("nexus_u_pipeline_outcomes_total", outcome="released")
        except BudgetExceeded as exc:
            record.unresolved_obligations.append(str(exc))
            resource_id = graph.add_node(
                str(exc),
                kind=ObligationKind.RESOURCE,
                severity=Severity.HIGH,
                source="resource.guard",
            )
            graph.defer(resource_id, reason="Resource budget exceeded", retry_conditions=["Increase declared budget", "Lower artifact resource demands"])
            if RunStatus.PARTIAL in ALLOWED[record.status]:
                self._terminal(record, chain, RunStatus.PARTIAL, "Resource budget exceeded")
            else:
                record.status = RunStatus.PARTIAL
                event = StageEvent(stage=RunStatus.PARTIAL, status="terminal", message="Resource budget exceeded")
                record.events.append(event)
                chain.append(event)
            METRICS.inc("nexus_u_pipeline_outcomes_total", outcome="budget_exceeded")
        except Exception as exc:
            message = f"Unhandled error: {type(exc).__name__}: {exc}"
            record.unresolved_obligations.append(message)
            unknown_id = graph.add_node(message, kind=ObligationKind.UNKNOWN, severity=Severity.CRITICAL, source="pipeline.exception")
            graph.escalate(unknown_id, reason="Unhandled pipeline exception", owner="operator")
            if record.status not in {RunStatus.RELEASED, RunStatus.REJECTED, RunStatus.PARTIAL, RunStatus.REFUTED, RunStatus.UNKNOWN}:
                record.status = RunStatus.UNKNOWN
                event = StageEvent(
                    stage=RunStatus.UNKNOWN,
                    status="terminal",
                    message="Unhandled pipeline failure",
                    metadata={"error": repr(exc)},
                )
                record.events.append(event)
                chain.append(event)
            METRICS.inc("nexus_u_pipeline_outcomes_total", outcome="unknown")
        finally:
            METRICS.set_gauge("nexus_u_pipeline_active", 0)

        return record, self._persist(record, chain, graph)
