from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from typing import Any


@dataclass(slots=True)
class CrossRepositoryObligation:
    source_repository: str
    source_obligation_id: str
    target_repository: str
    target_obligation_id: str
    relation: str = "DEPENDS_ON"
    required_digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def graph_digest(graph: dict[str, Any]) -> str:
    payload = json.dumps(graph, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def namespace_graph(repository: str, graph: dict[str, Any]) -> dict[str, Any]:
    node_map = {node["node_id"]: f"{repository}:{node['node_id']}" for node in graph.get("nodes", [])}
    nodes = []
    for node in graph.get("nodes", []):
        clone = dict(node)
        clone["node_id"] = node_map[node["node_id"]]
        clone.setdefault("metadata", {})["repository"] = repository
        nodes.append(clone)
    edges = []
    for edge in graph.get("edges", []):
        clone = dict(edge)
        clone["edge_id"] = f"{repository}:{edge['edge_id']}"
        clone["source"] = node_map[edge["source"]]
        clone["target"] = node_map[edge["target"]]
        edges.append(clone)
    return {"repository": repository, "digest": graph_digest(graph), "nodes": nodes, "edges": edges}


def merge_graphs(
    graphs: dict[str, dict[str, Any]],
    links: list[CrossRepositoryObligation] | None = None,
) -> dict[str, Any]:
    merged_nodes: list[dict[str, Any]] = []
    merged_edges: list[dict[str, Any]] = []
    repositories: dict[str, str] = {}
    for repository, graph in sorted(graphs.items()):
        namespaced = namespace_graph(repository, graph)
        repositories[repository] = namespaced["digest"]
        merged_nodes.extend(namespaced["nodes"])
        merged_edges.extend(namespaced["edges"])
    unresolved_links: list[dict[str, Any]] = []
    for index, link in enumerate(links or []):
        source = f"{link.source_repository}:{link.source_obligation_id}"
        target = f"{link.target_repository}:{link.target_obligation_id}"
        node_ids = {item["node_id"] for item in merged_nodes}
        if source not in node_ids or target not in node_ids:
            unresolved_links.append(link.to_dict())
            continue
        if link.required_digest and repositories.get(link.target_repository) != link.required_digest:
            unresolved_links.append(link.to_dict())
            continue
        merged_edges.append({
            "edge_id": f"cross:{index}:{source}->{target}",
            "source": source,
            "target": target,
            "relation": link.relation,
            "metadata": {"cross_repository": True},
        })
    return {
        "schema": "https://nexus-u.dev/federated-obligation-graph/v1",
        "repositories": repositories,
        "nodes": merged_nodes,
        "edges": merged_edges,
        "unresolved_links": unresolved_links,
        "federation_valid": not unresolved_links,
    }
