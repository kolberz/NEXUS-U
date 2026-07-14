from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Any

from nexus_u.core.models import ArtifactRecord
from nexus_u.routing.models import RoutingOutcome
from nexus_u.federation.models import EvidenceSubmission, FederationDecision


class ControlStore:
    def __init__(self, path: Path | str = "nexus-u.db") -> None:
        self.path = str(path)
        self._lock = Lock()
        self._initialize()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    released INTEGER NOT NULL,
                    artifact_path TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    task_payload TEXT NOT NULL,
                    artifact_id TEXT,
                    artifact_path TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS obligations (
                    artifact_id TEXT NOT NULL,
                    obligation_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    blocking INTEGER NOT NULL,
                    statement TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (artifact_id, obligation_id)
                );
                CREATE INDEX IF NOT EXISTS idx_obligations_status ON obligations(status);
                CREATE INDEX IF NOT EXISTS idx_obligations_kind ON obligations(kind);
                CREATE INDEX IF NOT EXISTS idx_obligations_artifact ON obligations(artifact_id);
                CREATE TABLE IF NOT EXISTS obligation_edges (
                    artifact_id TEXT NOT NULL,
                    edge_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (artifact_id, edge_id)
                );
                CREATE INDEX IF NOT EXISTS idx_edges_artifact ON obligation_edges(artifact_id);
                CREATE TABLE IF NOT EXISTS routing_outcomes (
                    outcome_id TEXT PRIMARY KEY,
                    obligation_signature TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    cost_seconds REAL NOT NULL,
                    debt_delta REAL NOT NULL,
                    artifact_id TEXT,
                    obligation_id TEXT,
                    result TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_routing_signature ON routing_outcomes(obligation_signature);
                CREATE INDEX IF NOT EXISTS idx_routing_strategy ON routing_outcomes(strategy);
                CREATE INDEX IF NOT EXISTS idx_routing_created ON routing_outcomes(created_at);
                CREATE TABLE IF NOT EXISTS federation_evidence (
                    submission_id TEXT PRIMARY KEY,
                    obligation_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    provenance_group TEXT NOT NULL,
                    evidence_digest TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_fed_evidence_obligation ON federation_evidence(obligation_id);
                CREATE INDEX IF NOT EXISTS idx_fed_evidence_org ON federation_evidence(organization_id);
                CREATE TABLE IF NOT EXISTS federation_decisions (
                    decision_id TEXT PRIMARY KEY,
                    obligation_id TEXT NOT NULL,
                    policy_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    approved INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_fed_decision_obligation ON federation_decisions(obligation_id);
                CREATE TABLE IF NOT EXISTS tension_discoveries (
                    run_id TEXT PRIMARY KEY,
                    obligation_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    tension_score_before REAL NOT NULL,
                    tension_score_after REAL NOT NULL,
                    tension_reduction REAL NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tension_obligation ON tension_discoveries(obligation_id);
                CREATE INDEX IF NOT EXISTS idx_tension_status ON tension_discoveries(status);
                CREATE TABLE IF NOT EXISTS discovery_trials (
                    run_id TEXT PRIMARY KEY,
                    suite_id TEXT NOT NULL,
                    corpus_hash TEXT NOT NULL,
                    case_count INTEGER NOT NULL,
                    precision REAL NOT NULL,
                    recall REAL NOT NULL,
                    specificity REAL NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_trial_suite ON discovery_trials(suite_id);
                CREATE INDEX IF NOT EXISTS idx_trial_created ON discovery_trials(created_at);
                CREATE TABLE IF NOT EXISTS reproduction_runs (
                    run_id TEXT PRIMARY KEY,
                    protocol_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    evaluator_count INTEGER NOT NULL,
                    evaluator_quorum INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_reproduction_protocol ON reproduction_runs(protocol_hash);
                CREATE INDEX IF NOT EXISTS idx_reproduction_created ON reproduction_runs(created_at);
                CREATE TABLE IF NOT EXISTS lower_bound_runs (
                    run_id TEXT PRIMARY KEY,
                    challenge_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    integrity_valid INTEGER NOT NULL,
                    universal_status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_lower_bound_challenge ON lower_bound_runs(challenge_id);
                CREATE INDEX IF NOT EXISTS idx_lower_bound_created ON lower_bound_runs(created_at);
                CREATE TABLE IF NOT EXISTS lower_bound_search_runs (
                    run_id TEXT PRIMARY KEY,
                    challenge_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    candidate_count INTEGER NOT NULL,
                    blocked_count INTEGER NOT NULL,
                    restricted_progress INTEGER NOT NULL,
                    universal_status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_lower_bound_search_challenge ON lower_bound_search_runs(challenge_id);
                CREATE INDEX IF NOT EXISTS idx_lower_bound_search_created ON lower_bound_search_runs(created_at);
                CREATE TABLE IF NOT EXISTS formalized_lower_bound_runs (
                    run_id TEXT PRIMARY KEY,
                    challenge_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    certificate_valid INTEGER NOT NULL,
                    external_kernel_verified INTEGER NOT NULL,
                    universal_status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_formalized_lower_bound_challenge ON formalized_lower_bound_runs(challenge_id);
                CREATE INDEX IF NOT EXISTS idx_formalized_lower_bound_created ON formalized_lower_bound_runs(created_at);
                CREATE TABLE IF NOT EXISTS kernel_bridge_runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    external_kernel_available INTEGER NOT NULL,
                    external_kernel_verified INTEGER NOT NULL,
                    universal_status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_kernel_bridge_created ON kernel_bridge_runs(created_at);
                """
            )

    def index_artifact(self, record: ArtifactRecord, artifact_path: Path | str) -> None:
        payload = json.dumps(record.to_dict(), default=str, sort_keys=True)
        graph = record.obligation_graph or {}
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO artifacts(artifact_id, task_id, status, released, artifact_path, payload) VALUES(?,?,?,?,?,?)",
                (record.artifact_id, record.task.task_id, str(record.status), int(record.released), str(artifact_path), payload),
            )
            conn.execute("DELETE FROM obligations WHERE artifact_id=?", (record.artifact_id,))
            conn.execute("DELETE FROM obligation_edges WHERE artifact_id=?", (record.artifact_id,))
            conn.executemany(
                "INSERT INTO obligations(artifact_id, obligation_id, kind, status, severity, blocking, statement, source, payload) VALUES(?,?,?,?,?,?,?,?,?)",
                [
                    (
                        record.artifact_id,
                        node["node_id"],
                        str(node.get("kind", "UNKNOWN")),
                        str(node.get("status", "OPEN")),
                        str(node.get("severity", "MEDIUM")),
                        int(bool(node.get("blocking", True))),
                        str(node.get("statement", "")),
                        str(node.get("source", "runtime")),
                        json.dumps(node, sort_keys=True, default=str),
                    )
                    for node in nodes
                ],
            )
            conn.executemany(
                "INSERT INTO obligation_edges(artifact_id, edge_id, source_id, target_id, relation, payload) VALUES(?,?,?,?,?,?)",
                [
                    (
                        record.artifact_id,
                        edge["edge_id"],
                        edge["source"],
                        edge["target"],
                        str(edge["relation"]),
                        json.dumps(edge, sort_keys=True, default=str),
                    )
                    for edge in edges
                ],
            )

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM artifacts WHERE artifact_id=?", (artifact_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        return result

    def list_artifacts(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT artifact_id, task_id, status, released, artifact_path, created_at FROM artifacts ORDER BY created_at DESC LIMIT ?",
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_obligation_graph(self, artifact_id: str) -> dict[str, Any] | None:
        artifact = self.get_artifact(artifact_id)
        if artifact is None:
            return None
        payload = artifact["payload"]
        return payload.get("obligation_graph")

    def list_obligations(
        self,
        *,
        artifact_id: str | None = None,
        status: str | None = None,
        kind: str | None = None,
        blocking: bool | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        if artifact_id:
            clauses.append("artifact_id=?")
            values.append(artifact_id)
        if status:
            clauses.append("status=?")
            values.append(status)
        if kind:
            clauses.append("kind=?")
            values.append(kind)
        if blocking is not None:
            clauses.append("blocking=?")
            values.append(int(blocking))
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        values.append(max(1, min(limit, 1000)))
        query = (
            "SELECT artifact_id, obligation_id, kind, status, severity, blocking, statement, source, payload "
            f"FROM obligations{where} ORDER BY artifact_id, obligation_id LIMIT ?"
        )
        with self._connect() as conn:
            rows = conn.execute(query, values).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["blocking"] = bool(item["blocking"])
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        return result

    def obligation_summary(self, artifact_id: str) -> dict[str, Any] | None:
        artifact = self.get_artifact(artifact_id)
        if artifact is None:
            return None
        return artifact["payload"].get("obligation_summary")

    def obligation_metrics(self, artifact_id: str) -> dict[str, Any] | None:
        artifact = self.get_artifact(artifact_id)
        if artifact is None:
            return None
        return artifact["payload"].get("obligation_metrics")

    def create_job(self, job_id: str, task_payload: dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO jobs(job_id,status,task_payload) VALUES(?,?,?)",
                (job_id, "QUEUED", json.dumps(task_payload, sort_keys=True)),
            )

    def update_job(self, job_id: str, **values: Any) -> None:
        allowed = {"status", "artifact_id", "artifact_path", "error"}
        entries = [(key, value) for key, value in values.items() if key in allowed]
        if not entries:
            return
        assignments = ",".join(f"{key}=?" for key, _ in entries) + ",updated_at=CURRENT_TIMESTAMP"
        with self._lock, self._connect() as conn:
            conn.execute(f"UPDATE jobs SET {assignments} WHERE job_id=?", [value for _, value in entries] + [job_id])

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["task_payload"] = json.loads(result["task_payload"])
        return result
    def record_routing_outcome(self, outcome: RoutingOutcome | dict[str, Any]) -> None:
        raw = outcome.to_dict() if isinstance(outcome, RoutingOutcome) else dict(outcome)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO routing_outcomes(outcome_id, obligation_signature, strategy, success, cost_seconds, debt_delta, artifact_id, obligation_id, result, metadata, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(raw["outcome_id"]),
                    str(raw["obligation_signature"]),
                    str(raw["strategy"]),
                    int(bool(raw["success"])),
                    float(raw.get("cost_seconds", 0.0)),
                    float(raw.get("debt_delta", 0.0)),
                    raw.get("artifact_id"),
                    raw.get("obligation_id"),
                    str(raw.get("result", "")),
                    json.dumps(raw.get("metadata", {}), sort_keys=True, default=str),
                    float(raw.get("created_at", 0.0)),
                ),
            )

    def recent_routing_outcomes(self, obligation_signature: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM routing_outcomes WHERE obligation_signature=? ORDER BY created_at DESC LIMIT ?",
                (obligation_signature, max(1, min(limit, 500))),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["success"] = bool(item["success"])
            item["metadata"] = json.loads(item["metadata"])
            result.append(item)
        return result

    def routing_stats(self, obligation_signature: str | None = None) -> list[dict[str, Any]]:
        where = " WHERE obligation_signature=?" if obligation_signature else ""
        params: tuple[Any, ...] = (obligation_signature,) if obligation_signature else ()
        query = (
            "SELECT obligation_signature, strategy, COUNT(*) AS attempts, "
            "SUM(success) AS successes, AVG(cost_seconds) AS mean_cost_seconds, "
            "AVG(debt_delta) AS mean_debt_delta, MAX(created_at) AS latest_at "
            f"FROM routing_outcomes{where} GROUP BY obligation_signature, strategy ORDER BY obligation_signature, strategy"
        )
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def routing_summary(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS attempts, SUM(success) AS successes, AVG(cost_seconds) AS mean_cost_seconds, AVG(debt_delta) AS mean_debt_delta FROM routing_outcomes"
            ).fetchone()
            by_strategy = conn.execute(
                "SELECT strategy, COUNT(*) AS attempts, SUM(success) AS successes, AVG(cost_seconds) AS mean_cost_seconds FROM routing_outcomes GROUP BY strategy ORDER BY strategy"
            ).fetchall()
        attempts = int(row["attempts"] or 0)
        successes = int(row["successes"] or 0)
        return {
            "attempts": attempts,
            "successes": successes,
            "success_rate": round(successes / attempts, 6) if attempts else 0.0,
            "mean_cost_seconds": float(row["mean_cost_seconds"] or 0.0),
            "mean_debt_delta": float(row["mean_debt_delta"] or 0.0),
            "by_strategy": [dict(item) for item in by_strategy],
        }
    def record_federation_evidence(self, submission: EvidenceSubmission | dict[str, Any]) -> None:
        raw = submission.to_dict() if isinstance(submission, EvidenceSubmission) else dict(submission)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO federation_evidence(submission_id, obligation_id, actor_id, organization_id, verdict, provenance_group, evidence_digest, payload, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    str(raw["submission_id"]), str(raw["obligation_id"]), str(raw["actor_id"]),
                    str(raw["organization_id"]), str(raw["verdict"]), str(raw["provenance_group"]),
                    str(raw["evidence_digest"]), json.dumps(raw, sort_keys=True, default=str),
                    float(raw.get("created_at", 0.0)),
                ),
            )

    def list_federation_evidence(self, obligation_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        where = " WHERE obligation_id=?" if obligation_id else ""
        params: tuple[Any, ...] = (obligation_id, max(1, min(limit, 1000))) if obligation_id else (max(1, min(limit, 1000)),)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM federation_evidence{where} ORDER BY created_at DESC LIMIT ?", params
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        return result

    def record_federation_decision(self, decision: FederationDecision | dict[str, Any]) -> None:
        raw = decision.to_dict() if isinstance(decision, FederationDecision) else dict(decision)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO federation_decisions(decision_id, obligation_id, policy_id, status, approved, payload, created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    str(raw["decision_id"]), str(raw["obligation_id"]), str(raw["policy_id"]),
                    str(raw["status"]), int(bool(raw.get("approved", False))),
                    json.dumps(raw, sort_keys=True, default=str), float(raw.get("created_at", 0.0)),
                ),
            )

    def list_federation_decisions(self, obligation_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        where = " WHERE obligation_id=?" if obligation_id else ""
        params: tuple[Any, ...] = (obligation_id, max(1, min(limit, 1000))) if obligation_id else (max(1, min(limit, 1000)),)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM federation_decisions{where} ORDER BY created_at DESC LIMIT ?", params
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["approved"] = bool(item["approved"])
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        return result
    def record_tension_discovery(self, report: Any) -> None:
        raw = report.to_dict() if hasattr(report, "to_dict") else dict(report)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tension_discoveries(run_id, obligation_id, status, tension_score_before, tension_score_after, tension_reduction, payload, created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    str(raw["run_id"]), str(raw["obligation_id"]), str(raw["status"]),
                    float(raw.get("tension_score_before", 0.0)),
                    float(raw.get("tension_score_after", 0.0)),
                    float(raw.get("tension_reduction", 0.0)),
                    json.dumps(raw, sort_keys=True, default=str), float(raw.get("created_at", 0.0)),
                ),
            )

    def get_tension_discovery(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tension_discoveries WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        return item

    def list_tension_discoveries(self, obligation_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if obligation_id:
            query = "SELECT * FROM tension_discoveries WHERE obligation_id=? ORDER BY created_at DESC LIMIT ?"
            params = (obligation_id, max(1, min(limit, 1000)))
        else:
            query = "SELECT * FROM tension_discoveries ORDER BY created_at DESC LIMIT ?"
            params = (max(1, min(limit, 1000)),)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        return result


    def record_discovery_trial(self, report: Any) -> None:
        raw = report.to_dict() if hasattr(report, "to_dict") else dict(report)
        summary = raw.get("summary", {})
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO discovery_trials(run_id, suite_id, corpus_hash, case_count, precision, recall, specificity, payload, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    str(raw["run_id"]), str(raw["suite_id"]), str(raw["corpus_hash"]),
                    int(summary.get("case_count", 0)), float(summary.get("precision", 0.0)),
                    float(summary.get("recall", 0.0)), float(summary.get("specificity", 0.0)),
                    json.dumps(raw, sort_keys=True, default=str), float(raw.get("created_at", 0.0)),
                ),
            )

    def get_discovery_trial(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM discovery_trials WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        return item

    def list_discovery_trials(self, suite_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if suite_id:
            query = "SELECT * FROM discovery_trials WHERE suite_id=? ORDER BY created_at DESC LIMIT ?"
            params = (suite_id, max(1, min(limit, 1000)))
        else:
            query = "SELECT * FROM discovery_trials ORDER BY created_at DESC LIMIT ?"
            params = (max(1, min(limit, 1000)),)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        return result

    def record_reproduction(self, report: Any) -> None:
        raw = report.to_dict() if hasattr(report, "to_dict") else dict(report)
        summary = raw.get("summary", {})
        protocol = raw.get("protocol", {})
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO reproduction_runs(run_id, protocol_hash, status, evaluator_count, evaluator_quorum, payload, created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    str(raw["run_id"]), str(protocol.get("protocol_hash", "")),
                    str(summary.get("status", "UNKNOWN")), int(summary.get("evaluator_count", 0)),
                    int(summary.get("evaluator_quorum", 0)), json.dumps(raw, sort_keys=True, default=str),
                    float(raw.get("created_at", 0.0)),
                ),
            )

    def get_reproduction(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM reproduction_runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        return item

    def list_reproductions(self, protocol_hash: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if protocol_hash:
            query = "SELECT * FROM reproduction_runs WHERE protocol_hash=? ORDER BY created_at DESC LIMIT ?"
            params = (protocol_hash, max(1, min(limit, 1000)))
        else:
            query = "SELECT * FROM reproduction_runs ORDER BY created_at DESC LIMIT ?"
            params = (max(1, min(limit, 1000)),)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        return result

    def record_lower_bound_run(self, report: Any) -> None:
        raw = report.to_dict() if hasattr(report, "to_dict") else dict(report)
        summary = raw.get("summary", {})
        status = "OPEN_WITH_CONDITIONAL_ROUTE" if summary.get("matrix_transposition_route_conditional") else "OPEN"
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO lower_bound_runs(run_id, challenge_id, status, integrity_valid, universal_status, payload, created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    str(raw["run_id"]), str(raw["challenge_id"]), status,
                    int(bool(raw.get("integrity_valid", False))),
                    str(summary.get("unconditional_universal_lower_bound_status", "UNKNOWN")),
                    json.dumps(raw, sort_keys=True, default=str), float(raw.get("created_at", 0.0)),
                ),
            )

    def get_lower_bound_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM lower_bound_runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["integrity_valid"] = bool(item["integrity_valid"])
        item["payload"] = json.loads(item["payload"])
        return item

    def list_lower_bound_runs(self, challenge_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if challenge_id:
            query = "SELECT * FROM lower_bound_runs WHERE challenge_id=? ORDER BY created_at DESC LIMIT ?"
            params = (challenge_id, max(1, min(limit, 1000)))
        else:
            query = "SELECT * FROM lower_bound_runs ORDER BY created_at DESC LIMIT ?"
            params = (max(1, min(limit, 1000)),)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["integrity_valid"] = bool(item["integrity_valid"])
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        return result
    def record_lower_bound_search(self, report: Any) -> None:
        raw = report.to_dict() if hasattr(report, "to_dict") else dict(report)
        summary = raw.get("summary", {})
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO lower_bound_search_runs(run_id, challenge_id, status, candidate_count, blocked_count, restricted_progress, universal_status, payload, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    str(raw["run_id"]),
                    str(raw["challenge_id"]),
                    str(summary.get("active_search_status", "UNKNOWN")),
                    int(summary.get("candidate_count", 0)),
                    int(summary.get("blocked_count", 0)),
                    int(summary.get("derived_restricted_count", 0)),
                    str(summary.get("universal_offline_lower_bound_status", "UNKNOWN")),
                    json.dumps(raw, sort_keys=True, default=str),
                    float(raw.get("created_at", 0.0)),
                ),
            )

    def get_lower_bound_search(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM lower_bound_search_runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        return item

    def list_lower_bound_searches(self, challenge_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if challenge_id:
            query = "SELECT * FROM lower_bound_search_runs WHERE challenge_id=? ORDER BY created_at DESC LIMIT ?"
            params = (challenge_id, max(1, min(limit, 1000)))
        else:
            query = "SELECT * FROM lower_bound_search_runs ORDER BY created_at DESC LIMIT ?"
            params = (max(1, min(limit, 1000)),)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        return result


    def record_kernel_bridge(self, report: Any) -> None:
        raw = report.to_dict() if hasattr(report, "to_dict") else dict(report)
        execution = raw.get("execution", {})
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO kernel_bridge_runs(run_id, status, external_kernel_available, external_kernel_verified, universal_status, payload, created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    str(raw["run_id"]), str(raw.get("status", "UNKNOWN")),
                    int(bool(execution.get("available", False))),
                    int(bool(execution.get("verified", False))),
                    str(raw.get("universal_target_status", "UNKNOWN")),
                    json.dumps(raw, sort_keys=True, default=str), float(raw.get("created_at", 0.0)),
                ),
            )

    def get_kernel_bridge(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM kernel_bridge_runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["external_kernel_available"] = bool(item["external_kernel_available"])
        item["external_kernel_verified"] = bool(item["external_kernel_verified"])
        item["payload"] = json.loads(item["payload"])
        return item

    def list_kernel_bridges(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM kernel_bridge_runs ORDER BY created_at DESC LIMIT ?",
                (max(1, min(limit, 1000)),),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["external_kernel_available"] = bool(item["external_kernel_available"])
            item["external_kernel_verified"] = bool(item["external_kernel_verified"])
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        return result


    def record_formalized_lower_bound(self, report: Any) -> None:
        raw = report.to_dict() if hasattr(report, "to_dict") else dict(report)
        summary = raw.get("summary", {})
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO formalized_lower_bound_runs(run_id, challenge_id, status, certificate_valid, external_kernel_verified, universal_status, payload, created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    str(raw["run_id"]),
                    str(raw["challenge_id"]),
                    str(summary.get("formalization_status", "UNKNOWN")),
                    int(bool(summary.get("specialized_certificate_valid", False))),
                    int(bool(summary.get("external_kernel_verified", False))),
                    str(summary.get("universal_offline_lower_bound_status", "UNKNOWN")),
                    json.dumps(raw, sort_keys=True, default=str),
                    float(raw.get("created_at", 0.0)),
                ),
            )

    def get_formalized_lower_bound(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM formalized_lower_bound_runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["certificate_valid"] = bool(item["certificate_valid"])
        item["external_kernel_verified"] = bool(item["external_kernel_verified"])
        item["payload"] = json.loads(item["payload"])
        return item

    def list_formalized_lower_bounds(self, challenge_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if challenge_id:
            query = "SELECT * FROM formalized_lower_bound_runs WHERE challenge_id=? ORDER BY created_at DESC LIMIT ?"
            params = (challenge_id, max(1, min(limit, 1000)))
        else:
            query = "SELECT * FROM formalized_lower_bound_runs ORDER BY created_at DESC LIMIT ?"
            params = (max(1, min(limit, 1000)),)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["certificate_valid"] = bool(item["certificate_valid"])
            item["external_kernel_verified"] = bool(item["external_kernel_verified"])
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        return result
