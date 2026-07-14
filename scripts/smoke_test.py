from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.request


def get_json(url: str) -> dict:
    return json.loads(urllib.request.urlopen(url, timeout=10).read())


def post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(request, timeout=30).read())


def main() -> int:
    base = os.environ.get("NEXUS_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    health = get_json(f"{base}/health")
    if health.get("status") != "ok":
        raise RuntimeError("health check failed")
    task = {
        "intent": "Production obligation-conservation smoke test",
        "artifact_type": "document",
        "modes": ["SYSTEM_ARCHITECTURE", "POLICY_AND_COMPLIANCE"],
        "adapter": "document",
        "success_conditions": ["healthy"],
        "inputs": {"body": "healthy release"},
    }
    result = post_json(f"{base}/v1/run", task)
    artifact = result.get("artifact", {})
    artifact_id = artifact.get("artifact_id")
    graph = get_json(f"{base}/v1/artifacts/{artifact_id}/obligations") if artifact_id else {}
    summary = graph.get("summary", {})
    now = __import__("time").time()
    routing_graph = {
        "graph_id": "smoke-routing",
        "created_at": now,
        "nodes": [{
            "node_id": "resource-duty",
            "statement": "Fit execution inside declared memory budget",
            "kind": "RESOURCE",
            "status": "OPEN",
            "severity": "HIGH",
            "blocking": True,
            "source": "smoke",
            "metadata": {},
            "created_at": now,
            "updated_at": now
        }],
        "edges": [],
        "events": []
    }
    route = post_json(f"{base}/v1/route", {"graph": routing_graph, "node_id": "resource-duty"})
    post_json(f"{base}/v1/routing/outcomes", {
        "obligation_signature": route["obligation_signature"],
        "strategy": route["selected"],
        "success": True,
        "cost_seconds": 1.0,
        "debt_delta": -3.0,
        "result": "smoke route completed"
    })
    routing_stats = get_json(f"{base}/v1/routing/stats")
    tension_spec = {
        "obligation_id": "smoke:tension",
        "actors": [
            {"actor_id": "smoke-a", "organization_id": "org-a", "roles": ["REVIEWER"], "key_id": "a-key", "secret": "a-secret"},
            {"actor_id": "smoke-b", "organization_id": "org-b", "roles": ["VERIFIER"], "key_id": "b-key", "secret": "b-secret"}
        ],
        "submissions": [
            {"actor_id": "smoke-a", "organization_id": "org-a", "verdict": "SUPPORTS", "provenance_group": "a", "summary": "supports"},
            {"actor_id": "smoke-b", "organization_id": "org-b", "verdict": "REFUTES", "provenance_group": "b", "summary": "refutes"}
        ],
        "policy": {}
    }
    tension = post_json(f"{base}/v1/discovery/tension", tension_spec)["report"]
    tension_history = get_json(f"{base}/v1/discovery/tensions?obligation_id=smoke:tension")
    trial_suite = json.loads(Path("examples/trials/obligation-tension-corpus.json").read_text(encoding="utf-8"))
    trial_report = post_json(f"{base}/v1/discovery/trials", trial_suite)["report"]
    trial_history = get_json(f"{base}/v1/discovery/trials?suite_id={trial_report['suite_id']}")
    reproduction = post_json(f"{base}/v1/discovery/reproduction", {"sample_size": 8})["report"]
    reproduction_history = get_json(f"{base}/v1/discovery/reproductions?protocol_hash={reproduction['protocol']['protocol_hash']}")
    success = (
        artifact.get("status") == "RELEASED"
        and artifact.get("released") is True
        and summary.get("conservation_valid") is True
        and summary.get("blocking_unresolved_count") == 0
        and route.get("selected") == "RESOURCE_LOWERING"
        and routing_stats.get("attempts", 0) >= 1
        and tension.get("status") == "EXPERIMENT_RECOMMENDED"
        and tension.get("recommendation") is not None
        and len(tension_history.get("discoveries", [])) >= 1
        and trial_report.get("summary", {}).get("f1") == 1.0
        and trial_report.get("summary", {}).get("false_positives") == 0
        and len(trial_history.get("trials", [])) >= 1
        and reproduction.get("summary", {}).get("reproduced") is True
        and reproduction.get("summary", {}).get("external_independence_claimed") is False
        and len(reproduction_history.get("reproductions", [])) >= 1
    )
    print(
        json.dumps(
            {
                "health": health,
                "artifact_id": artifact_id,
                "artifact_status": artifact.get("status"),
                "released": artifact.get("released"),
                "obligation_summary": summary,
                "route": route,
                "routing_stats": routing_stats,
                "tension": tension,
                "tension_history_count": len(tension_history.get("discoveries", [])),
                "trial_summary": trial_report.get("summary"),
                "trial_history_count": len(trial_history.get("trials", [])),
                "reproduction_summary": reproduction.get("summary"),
                "reproduction_history_count": len(reproduction_history.get("reproductions", [])),
            },
            indent=2,
        )
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
