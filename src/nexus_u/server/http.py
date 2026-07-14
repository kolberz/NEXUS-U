from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import time
from urllib.parse import parse_qs, urlparse
import uuid

from nexus_u.adapters.registry import AdapterRegistry
from nexus_u.config import ConfigError, task_from_dict
from nexus_u.core.pipeline import Pipeline
from nexus_u.core.obligation_graph import ObligationGraph
from nexus_u.integrations.capabilities import capability_report
from nexus_u.federation import load_federation_spec
from nexus_u.tension import TensionDiscoveryEngine, load_tension_spec
from nexus_u.lower_bounds import load_challenge
from nexus_u.trials import DiscoveryTrialRunner, load_trial_suite
from nexus_u.benchmark.external import run_independent_challenge
from nexus_u.benchmark.reproduction import run_preregistered_reproduction
from nexus_u.benchmark.lower_bound import run_lower_bound_benchmark
from nexus_u.benchmark.lower_bound_search import run_active_lower_bound_search_benchmark
from nexus_u.benchmark.formalized_lower_bound import run_formalized_lower_bound_benchmark
from nexus_u.benchmark.kernel_bridge import run_kernel_bridge_benchmark
from nexus_u import __version__
from nexus_u.jobs.manager import JobManager
from nexus_u.observability.metrics import METRICS
from nexus_u.orchestration.planner import build_workflow_plan
from nexus_u.routing import ObligationRouter, RoutingOutcome, Strategy
from nexus_u.storage.sqlite import ControlStore


_DATA_DIR = Path(os.environ.get("NEXUS_U_DATA_DIR", ".nexus-u"))
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_STORE = ControlStore(_DATA_DIR / "control.db")
_PIPELINE = Pipeline(output_dir=_DATA_DIR / "artifacts", store=_STORE)
_JOBS = JobManager(_STORE, pipeline_factory=lambda: Pipeline(output_dir=_DATA_DIR / "artifacts", store=_STORE))

_PUBLIC_ROUTES = {"/health", "/health/live", "/health/ready"}
_TRUE_VALUES = {"1", "true", "yes", "on"}
_MAX_QUERY_LIMIT = 1000


def _bounded_query(raw_query: str) -> dict[str, list[str]]:
    query = parse_qs(raw_query, keep_blank_values=True, max_num_fields=100)
    if "limit" not in query:
        return query
    limit = int(query["limit"][0])
    if limit < 1:
        raise ValueError("limit must be a positive integer")
    query["limit"] = [str(min(limit, _MAX_QUERY_LIMIT))]
    return query


class NexusHandler(BaseHTTPRequestHandler):
    pipeline = _PIPELINE
    store = _STORE
    jobs = _JOBS
    server_version = f"NEXUS-U/{__version__}"

    def _request_id(self) -> str:
        return self.headers.get("X-Request-ID") or str(uuid.uuid4())

    def _authorized(self, route: str) -> bool:
        if route in _PUBLIC_ROUTES:
            return True
        expected = os.environ.get("NEXUS_U_API_TOKEN")
        if not expected:
            setting = os.environ.get("NEXUS_U_ALLOW_UNAUTHENTICATED", "")
            return setting.strip().lower() in _TRUE_VALUES
        authorization = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not authorization.startswith(prefix):
            return False
        return hmac.compare_digest(
            authorization[len(prefix):].encode("utf-8"), expected.encode("utf-8")
        )

    def _headers(self, request_id: str, content_type: str, length: int) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Request-ID", request_id)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")

    def _send(self, status: int, payload: dict, *, request_id: str | None = None) -> None:
        request_id = request_id or self._request_id()
        data = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self._headers(request_id, "application/json", len(data))
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, status: int, text: str, content_type: str = "text/plain; charset=utf-8") -> None:
        request_id = self._request_id()
        data = text.encode("utf-8")
        self.send_response(status)
        self._headers(request_id, content_type, len(data))
        self.end_headers()
        self.wfile.write(data)

    def _begin(self) -> tuple[str, float, str]:
        request_id = self._request_id()
        route = urlparse(self.path).path
        started = time.monotonic()
        METRICS.inc("nexus_u_http_requests_total", method=self.command, route=route)
        return request_id, started, route

    def _finish(self, started: float, route: str, status: int) -> None:
        elapsed = time.monotonic() - started
        METRICS.inc("nexus_u_http_responses_total", route=route, status=status)
        METRICS.inc("nexus_u_http_duration_seconds_total", amount=elapsed, route=route)

    def do_GET(self) -> None:  # noqa: N802
        request_id, started, route = self._begin()
        if not self._authorized(route):
            self._send(401, {"error": "unauthorized"}, request_id=request_id)
            self._finish(started, route, 401)
            return
        parsed = urlparse(self.path)
        try:
            query = _bounded_query(parsed.query)
        except (ValueError, TypeError):
            self._send(
                400,
                {"error": "invalid_request", "detail": "limit must be a positive integer"},
                request_id=request_id,
            )
            self._finish(started, route, 400)
            return
        if route in {"/health", "/health/live"}:
            self._send(200, {"status": "ok", "service": "nexus-u", "version": __version__}, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route == "/health/ready":
            try:
                self.store.list_artifacts(1)
                payload, code = {"status": "ready", "storage": "ok"}, 200
            except Exception as exc:
                payload, code = {"status": "not_ready", "storage": type(exc).__name__}, 503
            self._send(code, payload, request_id=request_id)
            self._finish(started, route, code)
            return
        if route == "/metrics":
            self._send_text(200, METRICS.prometheus(), "text/plain; version=0.0.4; charset=utf-8")
            self._finish(started, route, 200)
            return
        if route == "/v1/events":
            limit = int(query.get("limit", ["100"])[0])
            self._send(200, {"events": METRICS.recent_events(limit)}, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route == "/v1/capabilities":
            report = capability_report()
            registry = AdapterRegistry()
            report["adapters"] = registry.descriptors()
            report["plugin_errors"] = registry.plugin_errors
            self._send(200, report, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route == "/v1/federation/evidence":
            obligation_id = query.get("obligation_id", [None])[0]
            limit = int(query.get("limit", ["100"])[0])
            self._send(200, {"evidence": self.store.list_federation_evidence(obligation_id, limit)}, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route == "/v1/federation/decisions":
            obligation_id = query.get("obligation_id", [None])[0]
            limit = int(query.get("limit", ["100"])[0])
            self._send(200, {"decisions": self.store.list_federation_decisions(obligation_id, limit)}, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route == "/v1/discovery/tensions":
            obligation_id = query.get("obligation_id", [None])[0]
            limit = int(query.get("limit", ["100"])[0])
            self._send(200, {"discoveries": self.store.list_tension_discoveries(obligation_id, limit)}, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route == "/v1/discovery/trials":
            suite_id = query.get("suite_id", [None])[0]
            limit = int(query.get("limit", ["100"])[0])
            self._send(200, {"trials": self.store.list_discovery_trials(suite_id, limit)}, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route.startswith("/v1/discovery/trials/"):
            run_id = route.rsplit("/", 1)[-1]
            report = self.store.get_discovery_trial(run_id)
            self._send(200 if report else 404, report or {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 200 if report else 404)
            return
        if route.startswith("/v1/discovery/tensions/"):
            run_id = route.rsplit("/", 1)[-1]
            report = self.store.get_tension_discovery(run_id)
            self._send(200 if report else 404, report or {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 200 if report else 404)
            return
        if route == "/v1/discovery/lower-bounds":
            challenge_id = query.get("challenge_id", [None])[0]
            limit = int(query.get("limit", ["100"])[0])
            self._send(200, {"runs": self.store.list_lower_bound_runs(challenge_id, limit)}, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route.startswith("/v1/discovery/lower-bounds/"):
            run_id = route.rsplit("/", 1)[-1]
            report = self.store.get_lower_bound_run(run_id)
            self._send(200 if report else 404, report or {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 200 if report else 404)
            return
        if route == "/v1/discovery/lower-bound-searches":
            challenge_id = query.get("challenge_id", [None])[0]
            limit = int(query.get("limit", ["100"])[0])
            self._send(200, {"runs": self.store.list_lower_bound_searches(challenge_id, limit)}, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route.startswith("/v1/discovery/lower-bound-searches/"):
            run_id = route.rsplit("/", 1)[-1]
            report = self.store.get_lower_bound_search(run_id)
            self._send(200 if report else 404, report or {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 200 if report else 404)
            return
        if route == "/v1/discovery/formalized-lower-bounds":
            challenge_id = query.get("challenge_id", [None])[0]
            limit = int(query.get("limit", ["100"])[0])
            self._send(200, {"runs": self.store.list_formalized_lower_bounds(challenge_id, limit)}, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route.startswith("/v1/discovery/formalized-lower-bounds/"):
            run_id = route.rsplit("/", 1)[-1]
            report = self.store.get_formalized_lower_bound(run_id)
            self._send(200 if report else 404, report or {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 200 if report else 404)
            return
        if route == "/v1/discovery/kernel-bridges":
            limit = int(query.get("limit", ["100"])[0])
            self._send(200, {"runs": self.store.list_kernel_bridges(limit)}, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route.startswith("/v1/discovery/kernel-bridges/"):
            run_id = route.rsplit("/", 1)[-1]
            report = self.store.get_kernel_bridge(run_id)
            self._send(200 if report else 404, report or {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 200 if report else 404)
            return
        if route == "/v1/discovery/reproductions":
            protocol_hash = query.get("protocol_hash", [None])[0]
            limit = int(query.get("limit", ["100"])[0])
            self._send(200, {"reproductions": self.store.list_reproductions(protocol_hash, limit)}, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route.startswith("/v1/discovery/reproductions/"):
            run_id = route.rsplit("/", 1)[-1]
            report = self.store.get_reproduction(run_id)
            self._send(200 if report else 404, report or {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 200 if report else 404)
            return
        if route == "/v1/artifacts":
            limit = int(query.get("limit", ["50"])[0])
            self._send(200, {"artifacts": self.store.list_artifacts(limit)}, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route == "/v1/routing/stats":
            signature = query.get("signature", [None])[0]
            payload = self.store.routing_summary()
            if signature:
                payload["signature_stats"] = self.store.routing_stats(signature)
                payload["recent"] = self.store.recent_routing_outcomes(signature, int(query.get("limit", ["20"])[0]))
            self._send(200, payload, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route == "/v1/obligations":
            limit = int(query.get("limit", ["100"])[0])
            blocking_raw = query.get("blocking", [None])[0]
            blocking = None if blocking_raw is None else blocking_raw.lower() in {"1", "true", "yes"}
            obligations = self.store.list_obligations(
                artifact_id=query.get("artifact_id", [None])[0],
                status=query.get("status", [None])[0],
                kind=query.get("kind", [None])[0],
                blocking=blocking,
                limit=limit,
            )
            self._send(200, {"obligations": obligations}, request_id=request_id)
            self._finish(started, route, 200)
            return
        if route.startswith("/v1/artifacts/") and route.endswith("/obligations"):
            artifact_id = route.split("/")[3]
            graph = self.store.get_obligation_graph(artifact_id)
            self._send(200 if graph else 404, graph or {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 200 if graph else 404)
            return
        if route.startswith("/v1/artifacts/") and route.endswith("/obligation-summary"):
            artifact_id = route.split("/")[3]
            summary = self.store.obligation_summary(artifact_id)
            self._send(200 if summary else 404, summary or {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 200 if summary else 404)
            return
        if route.startswith("/v1/artifacts/") and route.endswith("/obligation-metrics"):
            artifact_id = route.split("/")[3]
            metrics = self.store.obligation_metrics(artifact_id)
            self._send(200 if metrics else 404, metrics or {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 200 if metrics else 404)
            return
        if route.startswith("/v1/artifacts/") and route.endswith("/routes"):
            artifact_id = route.split("/")[3]
            artifact = self.store.get_artifact(artifact_id)
            routes = artifact["payload"].get("routing_recommendations", []) if artifact else None
            self._send(200 if artifact else 404, {"routing_recommendations": routes} if artifact else {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 200 if artifact else 404)
            return
        if route.startswith("/v1/artifacts/"):
            artifact_id = route.rsplit("/", 1)[-1]
            artifact = self.store.get_artifact(artifact_id)
            self._send(200 if artifact else 404, artifact or {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 200 if artifact else 404)
            return
        if route.startswith("/v1/jobs/"):
            job_id = route.rsplit("/", 1)[-1]
            job = self.store.get_job(job_id)
            self._send(200 if job else 404, job or {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 200 if job else 404)
            return
        self._send(404, {"error": "not_found"}, request_id=request_id)
        self._finish(started, route, 404)

    def do_POST(self) -> None:  # noqa: N802
        request_id, started, route = self._begin()
        if not self._authorized(route):
            self._send(401, {"error": "unauthorized"}, request_id=request_id)
            self._finish(started, route, 401)
            return
        if route not in {"/v1/run", "/v1/plan", "/v1/jobs", "/v1/obligations/verify", "/v1/route", "/v1/routing/outcomes", "/v1/federation/evaluate", "/v1/discovery/tension", "/v1/discovery/trials", "/v1/discovery/independent", "/v1/discovery/reproduction", "/v1/discovery/lower-bound", "/v1/discovery/lower-bound-search", "/v1/discovery/formalized-lower-bound", "/v1/discovery/kernel-bridge"}:
            self._send(404, {"error": "not_found"}, request_id=request_id)
            self._finish(started, route, 404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            max_body = int(os.environ.get("NEXUS_U_MAX_REQUEST_BYTES", "2000000"))
            if size <= 0 or size > max_body:
                self._send(413, {"error": "invalid_content_length"}, request_id=request_id)
                self._finish(started, route, 413)
                return
            raw = json.loads(self.rfile.read(size))
            if route == "/v1/federation/evaluate":
                ledger, obligation_id, policy = load_federation_spec(raw)
                decision = ledger.evaluate(obligation_id, policy)
                for item in ledger.evidence_for(obligation_id):
                    self.store.record_federation_evidence(item)
                self.store.record_federation_decision(decision)
                code = 200 if decision.approved else 422
                self._send(code, {"decision": decision.to_dict(), "evidence": [item.to_dict() for item in ledger.evidence_for(obligation_id)]}, request_id=request_id)
                self._finish(started, route, code)
                return
            if route == "/v1/discovery/tension":
                ledger, obligation_id, hypotheses, experiments, observed = load_tension_spec(raw)
                report = TensionDiscoveryEngine().run(
                    ledger, obligation_id, hypotheses=hypotheses or None, experiments=experiments or None, observed_result=observed
                )
                for item in ledger.evidence_for(obligation_id):
                    self.store.record_federation_evidence(item)
                self.store.record_tension_discovery(report)
                self._send(200, {"report": report.to_dict()}, request_id=request_id)
                self._finish(started, route, 200)
                return
            if route == "/v1/discovery/trials":
                suite_id, cases, metadata = load_trial_suite(raw)
                report = DiscoveryTrialRunner().run_suite(suite_id, cases, metadata)
                self.store.record_discovery_trial(report)
                self._send(200, {"report": report.to_dict()}, request_id=request_id)
                self._finish(started, route, 200)
                return
            if route == "/v1/discovery/independent":
                report, path = run_independent_challenge(
                    output_dir=_DATA_DIR / "benchmark-results",
                    signing_secret=os.environ.get("NEXUS_U_SIGNING_KEY"),
                    key_id="independent-challenge-http",
                )
                self._send(200, {"report": report.to_dict(), "path": str(path)}, request_id=request_id)
                self._finish(started, route, 200)
                return
            if route == "/v1/discovery/lower-bound":
                challenge = raw.get("challenge", raw if raw.get("challenge_id") else None)
                report, path = run_lower_bound_benchmark(
                    challenge,
                    output_dir=_DATA_DIR / "benchmark-results",
                    signing_secret=os.environ.get("NEXUS_U_SIGNING_KEY"),
                    key_id="lower-bound-lab-http",
                )
                self.store.record_lower_bound_run(report.lab_report)
                code = 200 if report.summary()["pass_rate"] == 1.0 else 422
                self._send(code, {"report": report.to_dict(), "path": str(path)}, request_id=request_id)
                self._finish(started, route, code)
                return
            if route == "/v1/discovery/lower-bound-search":
                report, path = run_active_lower_bound_search_benchmark(
                    output_dir=_DATA_DIR / "benchmark-results",
                    signing_secret=os.environ.get("NEXUS_U_SIGNING_KEY"),
                    key_id="active-lower-bound-search-http",
                    max_certificate_n=int(raw.get("max_certificate_n", 16)),
                )
                self.store.record_lower_bound_search(report.search_report)
                code = 200 if report.summary()["pass_rate"] == 1.0 else 422
                self._send(code, {"report": report.to_dict(), "path": str(path)}, request_id=request_id)
                self._finish(started, route, code)
                return
            if route == "/v1/discovery/formalized-lower-bound":
                report, path = run_formalized_lower_bound_benchmark(
                    output_dir=_DATA_DIR / "benchmark-results",
                    signing_secret=os.environ.get("NEXUS_U_SIGNING_KEY"),
                    key_id="formalized-lower-bound-http",
                )
                self.store.record_formalized_lower_bound(report.formalization_report)
                code = 200 if report.summary()["pass_rate"] == 1.0 else 422
                self._send(code, {"report": report.to_dict(), "path": str(path)}, request_id=request_id)
                self._finish(started, route, code)
                return
            if route == "/v1/discovery/kernel-bridge":
                report, path = run_kernel_bridge_benchmark(
                    output_dir=_DATA_DIR / "benchmark-results",
                    signing_secret=os.environ.get("NEXUS_U_SIGNING_KEY"),
                    key_id="kernel-bridge-http",
                    explicit_lean=raw.get("lean"),
                    explicit_lake=raw.get("lake"),
                )
                self.store.record_kernel_bridge(report.bridge_report)
                code = 200 if report.summary()["pass_rate"] == 1.0 else 422
                self._send(code, {"report": report.to_dict(), "path": str(path)}, request_id=request_id)
                self._finish(started, route, code)
                return
            if route == "/v1/discovery/reproduction":
                report, path = run_preregistered_reproduction(
                    output_dir=_DATA_DIR / "benchmark-results" / "reproduction",
                    seed=str(raw.get("seed", "nexus-u-v1.9-preregistered-seed")),
                    sample_size=int(raw["sample_size"]) if raw.get("sample_size") is not None else None,
                    signing_secret=os.environ.get("NEXUS_U_SIGNING_KEY"),
                    key_id="preregistered-reproduction-http",
                )
                self.store.record_reproduction(report)
                code = 200 if report.summary()["reproduced"] else 422
                self._send(code, {"report": report.to_dict(), "path": str(path)}, request_id=request_id)
                self._finish(started, route, code)
                return
            if route == "/v1/route":
                if raw.get("graph"):
                    graph = ObligationGraph.from_dict(raw["graph"])
                elif raw.get("artifact_id"):
                    graph_raw = self.store.get_obligation_graph(str(raw["artifact_id"]))
                    if graph_raw is None:
                        self._send(404, {"error": "artifact_not_found"}, request_id=request_id)
                        self._finish(started, route, 404)
                        return
                    graph = ObligationGraph.from_dict(graph_raw)
                else:
                    raise ValueError("Provide graph or artifact_id")
                node_id = raw.get("node_id")
                if not node_id:
                    unresolved = graph.unresolved()
                    if not unresolved:
                        raise ValueError("Graph contains no unresolved obligations")
                    node_id = unresolved[0].node_id
                decision = ObligationRouter(self.store).recommend(
                    graph, str(node_id), remaining_budget_seconds=raw.get("remaining_budget_seconds")
                )
                self._send(200, decision.to_dict(), request_id=request_id)
                self._finish(started, route, 200)
                return
            if route == "/v1/routing/outcomes":
                outcome = RoutingOutcome(
                    obligation_signature=str(raw["obligation_signature"]),
                    strategy=Strategy(str(raw["strategy"])),
                    success=bool(raw["success"]),
                    cost_seconds=float(raw["cost_seconds"]),
                    debt_delta=float(raw.get("debt_delta", 0.0)),
                    artifact_id=raw.get("artifact_id"),
                    obligation_id=raw.get("obligation_id"),
                    result=str(raw.get("result", "")),
                    metadata=dict(raw.get("metadata", {})),
                )
                self.store.record_routing_outcome(outcome)
                self._send(201, {"recorded": True, "outcome": outcome.to_dict()}, request_id=request_id)
                self._finish(started, route, 201)
                return
            if route == "/v1/obligations/verify":
                graph_raw = raw.get("graph", raw)
                graph = ObligationGraph.from_dict(graph_raw)
                valid, errors = graph.verify_conservation()
                payload = {"valid": valid, "errors": errors, "summary": graph.summary(), "promotion": graph.promotion_decision(raw.get("target", "RELEASED"))}
                self._send(200 if valid else 422, payload, request_id=request_id)
                self._finish(started, route, 200 if valid else 422)
                return
            if route == "/v1/jobs":
                task_from_dict(raw)  # validate before queueing
                job_id = self.jobs.submit(raw)
                self._send(202, {"job_id": job_id, "status": "QUEUED"}, request_id=request_id)
                self._finish(started, route, 202)
                return
            task = task_from_dict(raw)
            if route == "/v1/plan":
                self._send(200, build_workflow_plan(task), request_id=request_id)
                self._finish(started, route, 200)
                return
            record, path = self.pipeline.run(task)
            code = 200 if record.released else 422
            self._send(code, {"artifact": record.to_dict(), "path": str(path)}, request_id=request_id)
            self._finish(started, route, code)
        except (KeyError, ValueError, ConfigError, json.JSONDecodeError) as exc:
            self._send(400, {"error": "invalid_request", "detail": str(exc)}, request_id=request_id)
            self._finish(started, route, 400)
        except Exception as exc:
            self._send(500, {"error": "internal_error", "detail": type(exc).__name__}, request_id=request_id)
            self._finish(started, route, 500)

    def log_message(self, format: str, *args) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), NexusHandler)
    print(f"NEXUS-U listening on http://{host}:{port}")
    server.serve_forever()
