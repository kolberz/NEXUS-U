from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

from . import __version__
from .adapters.registry import AdapterRegistry
from .benchmark.reality import run_reality_benchmark
from .benchmark.routing import run_routing_benchmark
from .benchmark.federation import run_federation_benchmark
from .benchmark.tension import run_tension_benchmark
from .benchmark.trials import run_discovery_trials
from .benchmark.external import run_independent_challenge
from .benchmark.reproduction import run_preregistered_reproduction
from .benchmark.lower_bound import run_lower_bound_benchmark
from .benchmark.lower_bound_search import run_active_lower_bound_search_benchmark
from .benchmark.formalized_lower_bound import run_formalized_lower_bound_benchmark
from .benchmark.kernel_bridge import run_kernel_bridge_benchmark
from .benchmark.microkernel import run_cross_kernel_benchmark
from .benchmark.kernel_receipts import run_kernel_receipt_benchmark
from .benchmark.nexus_kernel import run_nexus_kernel_benchmark
from .benchmark.builtin import write_builtin_reality_suite
from .config import load_task
from .core.audit import sha256_value
from .core.pipeline import Pipeline
from .core.obligation_graph import ObligationGraph, load_obligation_graph
from .routing import ObligationRouter, RoutingOutcome, Strategy
from .core.policy import PolicyEngine, load_policy
from .integrations.capabilities import capability_report
from .federation import load_federation_spec
from .tension import TensionDiscoveryEngine, load_tension_spec
from .lower_bounds import ActiveLowerBoundSearchEngine, LowerBoundDiscoveryLab, load_challenge, write_report
from .trials import DiscoveryTrialRunner, load_trial_suite
from .observability.metrics import METRICS
from .orchestration.planner import build_workflow_plan
from .provenance.attestation import build_provenance_statement, verify_provenance_statement, write_statement
from .provenance.bundle import build_evidence_bundle, write_evidence_bundle
from .provenance.sbom import build_cyclonedx_sbom, write_sbom
from .security.signing import verify_signed_envelope, write_signed_envelope
from .server.http import serve
from .kernel import read_json as read_kernel_json, verify_bundle as verify_kernel_bundle
from .storage.sqlite import ControlStore


def cmd_run(args: argparse.Namespace) -> int:
    task = load_task(args.task)
    policy = PolicyEngine(load_policy(args.policy)) if args.policy else None
    store = ControlStore(args.database) if args.database else None
    record, path = Pipeline(output_dir=args.output, policy_engine=policy, store=store).run(task)
    print(json.dumps({
        "status": record.status,
        "artifact_id": record.artifact_id,
        "artifact_path": str(path),
        "evidence_bundle": str(Path(args.output) / record.evidence_bundle) if record.evidence_bundle else None,
        "audit_root": record.audit_root,
        "obligation_graph": str(Path(args.output) / record.obligation_graph_path) if record.obligation_graph_path else None,
        "obligation_summary": record.obligation_summary,
    }, indent=2, default=str))
    return 0 if record.released else 2


def cmd_validate(args: argparse.Namespace) -> int:
    task = load_task(args.task)
    registry = AdapterRegistry()
    decision = PolicyEngine(load_policy(args.policy) if args.policy else None).evaluate_preflight(task, registry.names())
    print(json.dumps({
        "valid": decision.allowed,
        "task_id": task.task_id,
        "fingerprint": sha256_value(task),
        "plan": build_workflow_plan(task),
        "policy": decision.to_dict(),
    }, indent=2))
    return 0 if decision.allowed else 2


def cmd_plan(args: argparse.Namespace) -> int:
    print(json.dumps(build_workflow_plan(load_task(args.task)), indent=2))
    return 0


def cmd_capabilities(args: argparse.Namespace) -> int:
    report = capability_report()
    registry = AdapterRegistry()
    report["adapters"] = registry.descriptors()
    report["plugin_errors"] = registry.plugin_errors
    print(json.dumps(report, indent=2))
    return 0


def cmd_attest(args: argparse.Namespace) -> int:
    statement = build_provenance_statement(
        args.subject,
        builder_id=args.builder_id,
        external_parameters={"source": args.source} if args.source else {},
    )
    output = args.output or f"{args.subject}.intoto.json"
    path = write_statement(statement, output)
    print(json.dumps({"attestation": str(path), "subject": args.subject}, indent=2))
    return 0


def cmd_verify_attestation(args: argparse.Namespace) -> int:
    statement = json.loads(Path(args.attestation).read_text(encoding="utf-8"))
    valid, errors = verify_provenance_statement(statement, args.subject)
    print(json.dumps({"valid": valid, "errors": errors}, indent=2))
    return 0 if valid else 2


def cmd_sbom(args: argparse.Namespace) -> int:
    output = args.output or f"{Path(args.subject).name}.cdx.json"
    path = write_sbom(build_cyclonedx_sbom(args.subject), output)
    print(json.dumps({"sbom": str(path)}, indent=2))
    return 0


def cmd_bundle(args: argparse.Namespace) -> int:
    bundle = build_evidence_bundle(args.artifact, audit_path=args.audit, obligation_graph_path=args.obligations)
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    output = args.output or f"{args.artifact}.evidence.json"
    path = write_evidence_bundle(bundle, output, secret=secret, key_id=args.key_id)
    print(json.dumps({"bundle": str(path), "signed": bool(secret)}, indent=2))
    return 0


def cmd_verify_bundle(args: argparse.Namespace) -> int:
    envelope = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    if not secret:
        print(json.dumps({"valid": False, "errors": ["No HMAC secret supplied"]}, indent=2))
        return 2
    valid, errors = verify_signed_envelope(envelope, secret)
    print(json.dumps({"valid": valid, "errors": errors}, indent=2))
    return 0 if valid else 2


def cmd_artifacts(args: argparse.Namespace) -> int:
    store = ControlStore(args.database)
    print(json.dumps({"artifacts": store.list_artifacts(args.limit)}, indent=2, default=str))
    return 0



def cmd_obligations(args: argparse.Namespace) -> int:
    if args.graph:
        graph = load_obligation_graph(args.graph)
        payload = {"summary": graph.summary(), "promotion": graph.promotion_decision(args.target), "graph": graph.to_dict() if args.full else None}
    elif args.artifact_id:
        store = ControlStore(args.database)
        graph_raw = store.get_obligation_graph(args.artifact_id)
        if graph_raw is None:
            print(json.dumps({"error": "not_found", "artifact_id": args.artifact_id}, indent=2))
            return 2
        graph = ObligationGraph.from_dict(graph_raw)
        payload = {"summary": graph.summary(), "promotion": graph.promotion_decision(args.target), "graph": graph.to_dict() if args.full else None}
    else:
        raise ValueError("Provide --graph or --artifact-id")
    print(json.dumps(payload, indent=2, default=str))
    return 0 if payload["summary"]["conservation_valid"] else 2


def cmd_verify_obligations(args: argparse.Namespace) -> int:
    graph = load_obligation_graph(args.graph)
    valid, errors = graph.verify_conservation()
    result = {"valid": valid, "errors": errors, "summary": graph.summary(), "promotion": graph.promotion_decision(args.target)}
    print(json.dumps(result, indent=2, default=str))
    return 0 if valid else 2


def cmd_reality_benchmark(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    suite = args.suite
    if args.builtin:
        suite = str(write_builtin_reality_suite(Path(args.output) / "builtin-suite"))
    if not suite:
        raise ValueError("Provide a suite path or --builtin")
    report, path = run_reality_benchmark(
        suite,
        output_dir=args.output,
        signing_secret=secret,
        key_id=args.key_id,
    )
    payload = {"report": str(path), "signed": bool(secret), "summary": report.summary()}
    print(json.dumps(payload, indent=2, default=str))
    return 0 if report.summary()["expected_outcomes_matched"] == report.summary()["case_count"] else 2



def _load_route_graph(args: argparse.Namespace) -> tuple[ObligationGraph, str]:
    if args.graph:
        graph = load_obligation_graph(args.graph)
    elif args.artifact_id:
        store = ControlStore(args.database)
        raw = store.get_obligation_graph(args.artifact_id)
        if raw is None:
            raise ValueError(f"Artifact not found: {args.artifact_id}")
        graph = ObligationGraph.from_dict(raw)
    else:
        raise ValueError("Provide --graph or --artifact-id")
    node_id = args.node_id
    if not node_id:
        unresolved = graph.unresolved()
        if not unresolved:
            raise ValueError("Graph contains no unresolved obligations")
        node_id = unresolved[0].node_id
    if node_id not in graph.nodes:
        raise ValueError(f"Obligation not found: {node_id}")
    return graph, node_id


def cmd_route_obligation(args: argparse.Namespace) -> int:
    graph, node_id = _load_route_graph(args)
    store = ControlStore(args.database)
    decision = ObligationRouter(store).recommend(graph, node_id, remaining_budget_seconds=args.remaining_budget)
    print(json.dumps(decision.to_dict(), indent=2, default=str))
    return 0


def cmd_record_route(args: argparse.Namespace) -> int:
    store = ControlStore(args.database)
    outcome = RoutingOutcome(
        obligation_signature=args.signature,
        strategy=Strategy(args.strategy),
        success=args.success,
        cost_seconds=args.cost_seconds,
        debt_delta=args.debt_delta,
        artifact_id=args.artifact_id,
        obligation_id=args.obligation_id,
        result=args.result or "",
    )
    store.record_routing_outcome(outcome)
    print(json.dumps({"recorded": True, "outcome": outcome.to_dict()}, indent=2, default=str))
    return 0


def cmd_routing_stats(args: argparse.Namespace) -> int:
    store = ControlStore(args.database)
    payload = store.routing_summary()
    if args.signature:
        payload["signature_stats"] = store.routing_stats(args.signature)
        payload["recent"] = store.recent_routing_outcomes(args.signature, args.limit)
    print(json.dumps(payload, indent=2, default=str))
    return 0


def cmd_routing_benchmark(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    report, path = run_routing_benchmark(output_dir=args.output, signing_secret=secret, key_id=args.key_id)
    summary = report.summary()
    print(json.dumps({"report": str(path), "signed": bool(secret), "summary": summary}, indent=2, default=str))
    return 0 if summary["router_matches"] == summary["case_count"] else 2



def cmd_federation_evaluate(args: argparse.Namespace) -> int:
    ledger, obligation_id, policy = load_federation_spec(args.spec)
    decision = ledger.evaluate(obligation_id, policy)
    if args.database:
        store = ControlStore(args.database)
        for item in ledger.evidence_for(obligation_id):
            store.record_federation_evidence(item)
        store.record_federation_decision(decision)
    print(json.dumps({
        "decision": decision.to_dict(),
        "evidence": [item.to_dict() for item in ledger.evidence_for(obligation_id)],
    }, indent=2, default=str))
    return 0 if decision.approved else 2


def cmd_federation_benchmark(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    report, path = run_federation_benchmark(
        output_dir=args.output, signing_secret=secret, key_id=args.key_id
    )
    summary = report.summary()
    print(json.dumps({"report": str(path), "signed": bool(secret), "summary": summary}, indent=2))
    return 0 if summary["expected_outcomes_matched"] == summary["case_count"] else 2

def cmd_tension_discover(args: argparse.Namespace) -> int:
    ledger, obligation_id, hypotheses, experiments, observed = load_tension_spec(args.spec)
    report = TensionDiscoveryEngine().run(
        ledger, obligation_id, hypotheses=hypotheses or None, experiments=experiments or None, observed_result=observed
    )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{report.run_id}.tension.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    signed_path = None
    if secret:
        signed_path = write_signed_envelope(
            report.to_dict(), output / f"{report.run_id}.tension.signed.json", key_id=args.key_id, secret=secret
        )
    if args.database:
        ControlStore(args.database).record_tension_discovery(report)
    print(json.dumps({
        "report": str(path), "signed_report": str(signed_path) if signed_path else None,
        "run_id": report.run_id, "status": report.status,
        "tension_score_before": report.tension_score_before,
        "tension_score_after": report.tension_score_after,
        "tension_reduction": report.tension_reduction,
        "recommended_experiment": report.recommendation.to_dict() if report.recommendation else None,
    }, indent=2, default=str))
    return 0


def cmd_tension_benchmark(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    report, path = run_tension_benchmark(output_dir=args.output, signing_secret=secret, key_id=args.key_id)
    summary = report.summary()
    print(json.dumps({"report": str(path), "signed": bool(secret), "summary": summary}, indent=2))
    return 0 if summary["experiment_matches"] == summary["case_count"] else 2


def cmd_tension_history(args: argparse.Namespace) -> int:
    store = ControlStore(args.database)
    print(json.dumps({"discoveries": store.list_tension_discoveries(args.obligation_id, args.limit)}, indent=2, default=str))
    return 0


def cmd_discovery_trials(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    report, path = run_discovery_trials(
        args.suite, output_dir=args.output, signing_secret=secret, key_id=args.key_id
    )
    if args.database:
        ControlStore(args.database).record_discovery_trial(report)
    summary = report.summary()
    print(json.dumps({"report": str(path), "signed": bool(secret), "summary": summary}, indent=2))
    return 0 if summary["false_positives"] == 0 and summary["false_negatives"] == 0 else 2



def cmd_independent_challenge(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    report, path = run_independent_challenge(
        args.corpus, args.labels, args.registry,
        output_dir=args.output, signing_secret=secret, key_id=args.key_id,
    )
    summary = report.summary()
    print(json.dumps({"report": str(path), "signed": bool(secret), "summary": summary}, indent=2))
    return 0 if (
        summary["false_positives"] == 0
        and summary["false_negatives"] == 0
        and summary["label_firewall_verified"]
    ) else 2


def cmd_preregistered_reproduction(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    report, path = run_preregistered_reproduction(
        args.corpus, args.labels, args.registry,
        output_dir=args.output,
        seed=args.seed,
        sample_size=args.sample_size,
        signing_secret=secret,
        key_id=args.key_id,
    )
    if args.database:
        ControlStore(args.database).record_reproduction(report)
    summary = report.summary()
    print(json.dumps({"report": str(path), "signed": bool(secret), "summary": summary}, indent=2))
    return 0 if summary["reproduced"] else 2


def cmd_lower_bound_lab(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    report, path = run_lower_bound_benchmark(
        args.challenge, output_dir=args.output, signing_secret=secret, key_id=args.key_id
    )
    if args.database:
        ControlStore(args.database).record_lower_bound_run(report.lab_report)
    summary = report.summary()
    print(json.dumps({"report": str(path), "signed": bool(secret), "summary": summary}, indent=2, default=str))
    return 0 if summary["pass_rate"] == 1.0 else 2


def cmd_lower_bound_history(args: argparse.Namespace) -> int:
    store = ControlStore(args.database)
    print(json.dumps({"runs": store.list_lower_bound_runs(args.challenge_id, args.limit)}, indent=2, default=str))
    return 0


def cmd_lower_bound_search(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    report, path = run_active_lower_bound_search_benchmark(
        output_dir=args.output,
        signing_secret=secret,
        key_id=args.key_id,
        max_certificate_n=args.max_certificate_n,
    )
    if args.database:
        ControlStore(args.database).record_lower_bound_search(report.search_report)
    summary = report.summary()
    print(json.dumps({"report": str(path), "signed": bool(secret), "summary": summary}, indent=2, default=str))
    return 0 if summary["pass_rate"] == 1.0 else 2


def cmd_lower_bound_search_history(args: argparse.Namespace) -> int:
    store = ControlStore(args.database)
    print(json.dumps({"runs": store.list_lower_bound_searches(args.challenge_id, args.limit)}, indent=2, default=str))
    return 0


def cmd_formalized_lower_bound(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    report, path = run_formalized_lower_bound_benchmark(
        output_dir=args.output, signing_secret=secret, key_id=args.key_id
    )
    if args.database:
        ControlStore(args.database).record_formalized_lower_bound(report.formalization_report)
    summary = report.summary()
    print(json.dumps({"report": str(path), "signed": bool(secret), "summary": summary}, indent=2, default=str))
    return 0 if summary["pass_rate"] == 1.0 else 2




def cmd_cross_kernel(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    report, path = run_cross_kernel_benchmark(
        output_dir=args.output, signing_secret=secret, key_id=args.key_id
    )
    summary = report.summary()
    print(json.dumps({"report": str(path), "signed": bool(secret), "summary": summary}, indent=2, default=str))
    return 0 if summary["composed_restricted_result"] else 2


def cmd_nexus_kernel_benchmark(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    report, path = run_nexus_kernel_benchmark(
        output_dir=args.output, signing_secret=secret, key_id=args.key_id
    )
    summary = report.summary()
    print(json.dumps({"report": str(path), "signed": bool(secret), "summary": summary}, indent=2, default=str))
    return 0 if summary["kernel_status"] == "NEXUS_KERNEL_VERIFIED" else 2


def cmd_kernel_check(args: argparse.Namespace) -> int:
    bundle = read_kernel_json(args.bundle)
    result = verify_kernel_bundle(bundle)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("valid") and result.get("bundle_verified") else 2


def cmd_kernel_receipts(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    report, path = run_kernel_receipt_benchmark(
        output_dir=args.output, signing_secret=secret, key_id=args.key_id
    )
    summary = report.summary()
    print(json.dumps({"report": str(path), "signed": bool(secret), "summary": summary}, indent=2, default=str))
    return 0 if summary["pass_rate"] == 1.0 else 2

def cmd_kernel_bridge(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("NEXUS_U_SIGNING_KEY")
    report, path = run_kernel_bridge_benchmark(
        output_dir=args.output, signing_secret=secret, key_id=args.key_id,
        explicit_lean=args.lean, explicit_lake=args.lake,
    )
    if args.database:
        ControlStore(args.database).record_kernel_bridge(report.bridge_report)
    summary = report.summary()
    print(json.dumps({"report": str(path), "signed": bool(secret), "summary": summary}, indent=2, default=str))
    return 0 if summary["pass_rate"] == 1.0 else 2


def cmd_kernel_bridge_history(args: argparse.Namespace) -> int:
    store = ControlStore(args.database)
    print(json.dumps({"runs": store.list_kernel_bridges(args.limit)}, indent=2, default=str))
    return 0


def cmd_formalized_lower_bound_history(args: argparse.Namespace) -> int:
    store = ControlStore(args.database)
    print(json.dumps({"runs": store.list_formalized_lower_bounds(args.challenge_id, args.limit)}, indent=2, default=str))
    return 0


def cmd_trial_history(args: argparse.Namespace) -> int:
    store = ControlStore(args.database)
    print(json.dumps({"trials": store.list_discovery_trials(args.suite_id, args.limit)}, indent=2, default=str))
    return 0


def cmd_metrics(args: argparse.Namespace) -> int:
    print(METRICS.prometheus(), end="")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    sample = {
        "intent": "Produce a release-ready hello-world artifact",
        "artifact_type": "software",
        "modes": ["SOFTWARE_ENGINEERING"],
        "adapter": "python",
        "success_conditions": ["NEXUS-U READY"],
        "assumptions": ["Python 3.11 or newer"],
        "inputs": {"code": "print('NEXUS-U READY')"},
        "budget": {"wall_clock_seconds": 10, "memory_mb": 256, "output_bytes": 100000},
    }
    target.write_text(json.dumps(sample, indent=2), encoding="utf-8")
    print(target)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nexus-u")
    parser.add_argument("--version", action="version", version=f"nexus-u {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run a task manifest")
    run.add_argument("task")
    run.add_argument("--output", default="artifacts")
    run.add_argument("--policy")
    run.add_argument("--database")
    run.set_defaults(func=cmd_run)

    validate = sub.add_parser("validate", help="Validate, fingerprint, policy-check, and plan a task manifest")
    validate.add_argument("task")
    validate.add_argument("--policy")
    validate.set_defaults(func=cmd_validate)

    plan = sub.add_parser("plan", help="Render the provider-neutral workflow plan")
    plan.add_argument("task")
    plan.set_defaults(func=cmd_plan)

    capabilities = sub.add_parser("capabilities", help="Report optional external tools and adapter contracts")
    capabilities.set_defaults(func=cmd_capabilities)

    attest = sub.add_parser("attest", help="Create an in-toto Statement with SLSA provenance")
    attest.add_argument("subject")
    attest.add_argument("--output")
    attest.add_argument("--builder-id", default="https://nexus-u.dev/local-builder/v1")
    attest.add_argument("--source")
    attest.set_defaults(func=cmd_attest)

    verify_attestation = sub.add_parser("verify-attestation", help="Verify subject digest and provenance structure")
    verify_attestation.add_argument("attestation")
    verify_attestation.add_argument("subject")
    verify_attestation.set_defaults(func=cmd_verify_attestation)

    sbom = sub.add_parser("sbom", help="Generate a CycloneDX SBOM")
    sbom.add_argument("subject")
    sbom.add_argument("--output")
    sbom.set_defaults(func=cmd_sbom)

    bundle = sub.add_parser("bundle", help="Create an evidence bundle, optionally HMAC-authenticated")
    bundle.add_argument("artifact")
    bundle.add_argument("--audit")
    bundle.add_argument("--obligations")
    bundle.add_argument("--output")
    bundle.add_argument("--secret")
    bundle.add_argument("--key-id", default="local-hmac")
    bundle.set_defaults(func=cmd_bundle)

    verify_bundle = sub.add_parser("verify-bundle", help="Verify an HMAC-authenticated evidence bundle")
    verify_bundle.add_argument("bundle")
    verify_bundle.add_argument("--secret")
    verify_bundle.set_defaults(func=cmd_verify_bundle)

    artifacts = sub.add_parser("artifacts", help="List indexed artifacts")
    artifacts.add_argument("--database", default=".nexus-u/control.db")
    artifacts.add_argument("--limit", type=int, default=50)
    artifacts.set_defaults(func=cmd_artifacts)

    obligations = sub.add_parser("obligations", help="Inspect an obligation graph or indexed artifact")
    obligations.add_argument("--graph")
    obligations.add_argument("--artifact-id")
    obligations.add_argument("--database", default=".nexus-u/control.db")
    obligations.add_argument("--target", default="RELEASED")
    obligations.add_argument("--full", action="store_true")
    obligations.set_defaults(func=cmd_obligations)

    verify_obligations = sub.add_parser("verify-obligations", help="Verify conservation and promotion readiness of an obligation graph")
    verify_obligations.add_argument("graph")
    verify_obligations.add_argument("--target", default="RELEASED")
    verify_obligations.set_defaults(func=cmd_verify_obligations)

    benchmark = sub.add_parser("reality-benchmark", help="Compare a tests-only baseline with obligation-centered delivery")
    benchmark.add_argument("suite", nargs="?")
    benchmark.add_argument("--builtin", action="store_true", help="Materialize and run the built-in Reality Loop suite")
    benchmark.add_argument("--output", default="benchmark-results")
    benchmark.add_argument("--secret")
    benchmark.add_argument("--key-id", default="reality-loop-local")
    benchmark.set_defaults(func=cmd_reality_benchmark)

    route = sub.add_parser("route-obligation", help="Recommend the next strategy for an unresolved obligation")
    route.add_argument("--graph")
    route.add_argument("--artifact-id")
    route.add_argument("--node-id")
    route.add_argument("--database", default=".nexus-u/control.db")
    route.add_argument("--remaining-budget", type=float)
    route.set_defaults(func=cmd_route_obligation)

    record_route = sub.add_parser("record-route", help="Record a routing outcome for learning")
    record_route.add_argument("signature")
    record_route.add_argument("strategy", choices=[item.value for item in Strategy])
    result_group = record_route.add_mutually_exclusive_group(required=True)
    result_group.add_argument("--success", action="store_true")
    result_group.add_argument("--failure", dest="success", action="store_false")
    record_route.add_argument("--cost-seconds", type=float, required=True)
    record_route.add_argument("--debt-delta", type=float, default=0.0)
    record_route.add_argument("--artifact-id")
    record_route.add_argument("--obligation-id")
    record_route.add_argument("--result")
    record_route.add_argument("--database", default=".nexus-u/control.db")
    record_route.set_defaults(func=cmd_record_route)

    routing_stats = sub.add_parser("routing-stats", help="Inspect learned routing outcomes")
    routing_stats.add_argument("--database", default=".nexus-u/control.db")
    routing_stats.add_argument("--signature")
    routing_stats.add_argument("--limit", type=int, default=20)
    routing_stats.set_defaults(func=cmd_routing_stats)

    routing_benchmark = sub.add_parser("routing-benchmark", help="Validate the learned obligation router against a static baseline")
    routing_benchmark.add_argument("--output", default="benchmark-results")
    routing_benchmark.add_argument("--secret")
    routing_benchmark.add_argument("--key-id", default="obligation-router-local")
    routing_benchmark.set_defaults(func=cmd_routing_benchmark)


    federation_evaluate = sub.add_parser("federation-evaluate", help="Evaluate signed multi-organization evidence against a quorum policy")
    federation_evaluate.add_argument("spec")
    federation_evaluate.add_argument("--database")
    federation_evaluate.set_defaults(func=cmd_federation_evaluate)

    federation_benchmark = sub.add_parser("federation-benchmark", help="Validate federated evidence, conflict, veto, and dependency rules")
    federation_benchmark.add_argument("--output", default="benchmark-results")
    federation_benchmark.add_argument("--secret")
    federation_benchmark.add_argument("--key-id", default="federated-evidence-local")
    federation_benchmark.set_defaults(func=cmd_federation_benchmark)

    tension_discover = sub.add_parser("tension-discover", help="Detect obligation tension and design a discriminating experiment")
    tension_discover.add_argument("spec")
    tension_discover.add_argument("--output", default="tension-results")
    tension_discover.add_argument("--database")
    tension_discover.add_argument("--secret")
    tension_discover.add_argument("--key-id", default="tension-discovery-local")
    tension_discover.set_defaults(func=cmd_tension_discover)

    tension_benchmark = sub.add_parser("tension-benchmark", help="Validate tension-driven discovery against a static novelty baseline")
    tension_benchmark.add_argument("--output", default="benchmark-results")
    tension_benchmark.add_argument("--secret")
    tension_benchmark.add_argument("--key-id", default="tension-discovery-local")
    tension_benchmark.set_defaults(func=cmd_tension_benchmark)

    tension_history = sub.add_parser("tension-history", help="List persisted tension-driven discovery runs")
    tension_history.add_argument("--database", default=".nexus-u/control.db")
    tension_history.add_argument("--obligation-id")
    tension_history.add_argument("--limit", type=int, default=100)
    tension_history.set_defaults(func=cmd_tension_history)

    discovery_trials = sub.add_parser("discovery-trials", help="Run blind provenance-bearing discovery trials")
    discovery_trials.add_argument("suite", nargs="?", help="Trial suite JSON; defaults to the built-in corpus")
    discovery_trials.add_argument("--output", default="benchmark-results")
    discovery_trials.add_argument("--database")
    discovery_trials.add_argument("--secret")
    discovery_trials.add_argument("--key-id", default="discovery-trials-local")
    discovery_trials.set_defaults(func=cmd_discovery_trials)


    independent = sub.add_parser("independent-challenge", help="Run the external held-out discovery challenge")
    independent.add_argument("--corpus")
    independent.add_argument("--labels")
    independent.add_argument("--registry")
    independent.add_argument("--output", default="benchmark-results")
    independent.add_argument("--secret")
    independent.add_argument("--key-id", default="independent-challenge-local")
    independent.set_defaults(func=cmd_independent_challenge)


    reproduction = sub.add_parser("preregistered-reproduction", help="Run an immutable preregistered process-isolated reproduction")
    reproduction.add_argument("--corpus")
    reproduction.add_argument("--labels")
    reproduction.add_argument("--registry")
    reproduction.add_argument("--output", default="benchmark-results/reproduction")
    reproduction.add_argument("--seed", default="nexus-u-v1.9-preregistered-seed")
    reproduction.add_argument("--sample-size", type=int)
    reproduction.add_argument("--database")
    reproduction.add_argument("--secret")
    reproduction.add_argument("--key-id", default="preregistered-reproduction-local")
    reproduction.set_defaults(func=cmd_preregistered_reproduction)

    lower_bound = sub.add_parser("lower-bound-lab", help="Run the model-aware integer-multiplication lower-bound laboratory")
    lower_bound.add_argument("challenge", nargs="?", help="Challenge JSON; defaults to the built-in registry")
    lower_bound.add_argument("--output", default="benchmark-results")
    lower_bound.add_argument("--database")
    lower_bound.add_argument("--secret")
    lower_bound.add_argument("--key-id", default="lower-bound-lab-local")
    lower_bound.set_defaults(func=cmd_lower_bound_lab)

    lower_bound_history = sub.add_parser("lower-bound-history", help="List persisted lower-bound laboratory runs")
    lower_bound_history.add_argument("--database", default=".nexus-u/control.db")
    lower_bound_history.add_argument("--challenge-id")
    lower_bound_history.add_argument("--limit", type=int, default=100)
    lower_bound_history.set_defaults(func=cmd_lower_bound_history)

    lower_bound_search = sub.add_parser("lower-bound-search", help="Run obligation-weighted active lower-bound proof-route search")
    lower_bound_search.add_argument("--output", default="benchmark-results")
    lower_bound_search.add_argument("--database")
    lower_bound_search.add_argument("--secret")
    lower_bound_search.add_argument("--key-id", default="active-lower-bound-search-local")
    lower_bound_search.add_argument("--max-certificate-n", type=int, default=16)
    lower_bound_search.set_defaults(func=cmd_lower_bound_search)

    lower_bound_search_history = sub.add_parser("lower-bound-search-history", help="List persisted active lower-bound search runs")
    lower_bound_search_history.add_argument("--database", default=".nexus-u/control.db")
    lower_bound_search_history.add_argument("--challenge-id")
    lower_bound_search_history.add_argument("--limit", type=int, default=100)
    lower_bound_search_history.set_defaults(func=cmd_lower_bound_search_history)

    formalized_lower_bound = sub.add_parser("formalized-lower-bound", help="Run specialized proof-certificate checking and generate proof-assistant targets")
    formalized_lower_bound.add_argument("--output", default="benchmark-results")
    formalized_lower_bound.add_argument("--database")
    formalized_lower_bound.add_argument("--secret")
    formalized_lower_bound.add_argument("--key-id", default="formalized-lower-bound-local")
    formalized_lower_bound.set_defaults(func=cmd_formalized_lower_bound)


    cross_kernel = sub.add_parser("cross-kernel", help="Cross-check the restricted lower bound with independent arithmetic and logical kernels")
    cross_kernel.add_argument("--output", default="benchmark-results")
    cross_kernel.add_argument("--secret")
    cross_kernel.add_argument("--key-id", default="cross-kernel-local")
    cross_kernel.set_defaults(func=cmd_cross_kernel)


    nexus_kernel = sub.add_parser("nexus-kernel-benchmark", help="Validate the native NEXUS dependent-type kernel")
    nexus_kernel.add_argument("--output", default="benchmark-results")
    nexus_kernel.add_argument("--secret")
    nexus_kernel.add_argument("--key-id", default="nexus-kernel-local")
    nexus_kernel.set_defaults(func=cmd_nexus_kernel_benchmark)

    kernel_check = sub.add_parser("kernel-check", help="Replay a serialized NEXUS Kernel proof bundle")
    kernel_check.add_argument("bundle")
    kernel_check.set_defaults(func=cmd_kernel_check)

    kernel_receipts = sub.add_parser("kernel-receipts", help="Generate and evaluate federated external-kernel receipt requests")
    kernel_receipts.add_argument("--output", default="benchmark-results")
    kernel_receipts.add_argument("--secret")
    kernel_receipts.add_argument("--key-id", default="kernel-receipt-local")
    kernel_receipts.set_defaults(func=cmd_kernel_receipts)

    kernel_bridge = sub.add_parser("kernel-bridge", help="Generate and, when available, execute the pinned Lean kernel bridge")
    kernel_bridge.add_argument("--output", default="benchmark-results")
    kernel_bridge.add_argument("--database")
    kernel_bridge.add_argument("--secret")
    kernel_bridge.add_argument("--key-id", default="kernel-bridge-local")
    kernel_bridge.add_argument("--lean")
    kernel_bridge.add_argument("--lake")
    kernel_bridge.set_defaults(func=cmd_kernel_bridge)

    kernel_bridge_history = sub.add_parser("kernel-bridge-history", help="List persisted kernel-bridge runs")
    kernel_bridge_history.add_argument("--database", default=".nexus-u/control.db")
    kernel_bridge_history.add_argument("--limit", type=int, default=100)
    kernel_bridge_history.set_defaults(func=cmd_kernel_bridge_history)

    formalized_history = sub.add_parser("formalized-lower-bound-history", help="List persisted formalized lower-bound runs")
    formalized_history.add_argument("--database", default=".nexus-u/control.db")
    formalized_history.add_argument("--challenge-id")
    formalized_history.add_argument("--limit", type=int, default=100)
    formalized_history.set_defaults(func=cmd_formalized_lower_bound_history)

    trial_history = sub.add_parser("trial-history", help="List persisted discovery trial runs")
    trial_history.add_argument("--database", default=".nexus-u/control.db")
    trial_history.add_argument("--suite-id")
    trial_history.add_argument("--limit", type=int, default=100)
    trial_history.set_defaults(func=cmd_trial_history)

    metrics = sub.add_parser("metrics", help="Print in-process Prometheus metrics")
    metrics.set_defaults(func=cmd_metrics)

    init = sub.add_parser("init", help="Create a sample task manifest")
    init.add_argument("path", nargs="?", default="task.json")
    init.set_defaults(func=cmd_init)

    server = sub.add_parser("serve", help="Run the HTTP control plane")
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8080)
    server.set_defaults(func=lambda args: serve(args.host, args.port) or 0)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(args.func(args))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
