from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from nexus_u.core.obligation_graph import load_obligation_graph
from nexus_u.provenance.attestation import (
    build_provenance_statement,
    verify_provenance_statement,
    write_statement,
)
from nexus_u.security.signing import verify_signed_envelope

VERSION = "2.6.0"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def attest(path: Path, attestation_dir: Path) -> tuple[Path, list[str]]:
    statement = build_provenance_statement(
        path,
        builder_id="https://nexus-u.dev/release-gate/v2.6",
        external_parameters={
            "release_gate": "scripts/release_gate.py",
            "obligation_conservation": True,
            "reality_benchmark_required": True,
            "obligation_router_benchmark_required": True,
            "federated_evidence_benchmark_required": True,
            "tension_discovery_benchmark_required": True,
            "independent_discovery_challenge_required": True,
            "preregistered_reproduction_required": True,
            "active_lower_bound_search_required": True,
            "formalized_lower_bound_search_required": True,
            "kernel_verification_bridge_required": True,
            "kernel_receipt_federation_required": True,
            "native_nexus_kernel_required": True,
        },
    )
    output = write_statement(statement, attestation_dir / f"{path.name}.intoto.json")
    valid, errors = verify_provenance_statement(statement, path)
    return output, errors if not valid else []


def validate_benchmark(root: Path) -> tuple[list[Path], dict, list[str]]:
    failures: list[str] = []
    report_path = root / "benchmark-results/reality-benchmark.json"
    signed_path = root / "benchmark-results/reality-benchmark.signed.json"
    if not report_path.is_file():
        return [], {}, ["Reality benchmark report is missing"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    if summary.get("case_count", 0) < 4:
        failures.append("Reality benchmark must contain at least four cases")
    if summary.get("expected_outcome_rate") != 1.0:
        failures.append("Reality benchmark did not match all expected outcomes")
    if summary.get("hidden_obligations_caught", 0) < 1:
        failures.append("Reality benchmark did not demonstrate hidden-obligation detection")
    if summary.get("baseline_passes") != summary.get("case_count"):
        failures.append("Reality benchmark baseline did not pass every designed candidate")
    if summary.get("nexus_releases", 0) >= summary.get("baseline_passes", 0):
        failures.append("Reality benchmark did not distinguish obligation-centered delivery from baseline")

    files = [report_path]
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        if not signed_path.is_file():
            failures.append("Signed Reality benchmark envelope is missing")
        else:
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"Reality benchmark signature: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures



def validate_routing_benchmark(root: Path) -> tuple[list[Path], dict, list[str]]:
    failures: list[str] = []
    report_path = root / "benchmark-results/routing-benchmark.json"
    signed_path = root / "benchmark-results/routing-benchmark.signed.json"
    if not report_path.is_file():
        return [], {}, ["Obligation Router benchmark report is missing"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    if summary.get("case_count", 0) < 6:
        failures.append("Obligation Router benchmark must contain at least six cases")
    if summary.get("router_match_rate") != 1.0:
        failures.append("Obligation Router did not match all expected strategies")
    if summary.get("routing_advantage", 0) <= 0.5:
        failures.append("Obligation Router did not materially outperform the static baseline")
    if summary.get("escalations", 0) < 1:
        failures.append("Obligation Router benchmark did not exercise escalation policy")

    files = [report_path]
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        if not signed_path.is_file():
            failures.append("Signed Obligation Router benchmark envelope is missing")
        else:
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"Obligation Router benchmark signature: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures



def validate_federation_benchmark(root: Path) -> tuple[list[Path], dict, list[str]]:
    failures: list[str] = []
    report_path = root / "benchmark-results/federation-benchmark.json"
    signed_path = root / "benchmark-results/federation-benchmark.signed.json"
    if not report_path.is_file():
        return [], {}, ["Federated Evidence benchmark report is missing"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    if summary.get("case_count", 0) < 6:
        failures.append("Federated Evidence benchmark must contain at least six cases")
    if summary.get("match_rate") != 1.0:
        failures.append("Federated Evidence benchmark did not match all expected outcomes")
    if summary.get("approved_cases", 0) < 1:
        failures.append("Federated Evidence benchmark did not exercise approval")
    if summary.get("blocked_or_conflicted_cases", 0) < 4:
        failures.append("Federated Evidence benchmark did not exercise enough blocking conditions")
    files = [report_path]
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        if not signed_path.is_file():
            failures.append("Signed Federated Evidence benchmark envelope is missing")
        else:
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"Federated Evidence benchmark signature: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures

def validate_tension_benchmark(root: Path) -> tuple[list[Path], dict, list[str]]:
    failures: list[str] = []
    report_path = root / "benchmark-results/tension-benchmark.json"
    signed_path = root / "benchmark-results/tension-benchmark.signed.json"
    if not report_path.is_file():
        return [], {}, ["Tension-Driven Discovery benchmark report is missing"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    if summary.get("case_count", 0) < 6:
        failures.append("Tension-Driven Discovery benchmark must contain at least six cases")
    if summary.get("detection_rate") != 1.0:
        failures.append("Tension-Driven Discovery did not detect all designed tensions")
    if summary.get("experiment_match_rate") != 1.0:
        failures.append("Tension-Driven Discovery did not choose every discriminating experiment")
    if summary.get("discovery_advantage", 0) <= 0.5:
        failures.append("Tension-Driven Discovery did not materially outperform the static novelty baseline")
    if summary.get("tension_reduced_cases", 0) != summary.get("case_count", 0):
        failures.append("Tension-Driven Discovery did not reduce tension in every observed benchmark case")
    files = [report_path]
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        if not signed_path.is_file():
            failures.append("Signed Tension-Driven Discovery benchmark envelope is missing")
        else:
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"Tension-Driven Discovery benchmark signature: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures


def validate_discovery_trials(root: Path) -> tuple[list[Path], dict, list[str]]:
    failures: list[str] = []
    report_path = root / "benchmark-results/discovery-trials.json"
    signed_path = root / "benchmark-results/discovery-trials.signed.json"
    if not report_path.is_file():
        return [], {}, ["Discovery Trials report is missing"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    if summary.get("case_count", 0) < 10:
        failures.append("Discovery Trials must contain at least ten cases")
    if summary.get("positive_cases", 0) < 6:
        failures.append("Discovery Trials do not contain enough tension cases")
    if summary.get("negative_controls", 0) < 2:
        failures.append("Discovery Trials require no-tension controls")
    if summary.get("precision") != 1.0 or summary.get("recall") != 1.0:
        failures.append("Discovery Trials contain a false discovery or missed tension")
    if summary.get("specificity") != 1.0:
        failures.append("Discovery Trials failed clean abstention controls")
    if summary.get("kind_matches") != summary.get("positive_cases"):
        failures.append("Discovery Trials did not classify every detected tension correctly")
    if summary.get("experiment_matches") != summary.get("positive_cases"):
        failures.append("Discovery Trials did not choose the expected discriminating experiment family")
    if not report.get("corpus_hash"):
        failures.append("Discovery Trials corpus hash is missing")
    files = [report_path]
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        if not signed_path.is_file():
            failures.append("Signed Discovery Trials envelope is missing")
        else:
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"Discovery Trials signature: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures



def validate_independent_challenge(root: Path) -> tuple[list[Path], dict, list[str]]:
    failures: list[str] = []
    report_path = root / "benchmark-results/independent-discovery-challenge.json"
    signed_path = root / "benchmark-results/independent-discovery-challenge.signed.json"
    if not report_path.is_file():
        return [], {}, ["Independent Discovery Challenge report is missing"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    if summary.get("case_count", 0) < 8:
        failures.append("Independent Discovery Challenge must contain at least eight cases")
    if summary.get("external_sources", 0) < 3:
        failures.append("Independent Discovery Challenge must include at least three external datasets")
    if summary.get("positive_cases", 0) < 3:
        failures.append("Independent Discovery Challenge requires externally labeled tension cases")
    if summary.get("negative_controls", 0) < 3:
        failures.append("Independent Discovery Challenge requires external abstention controls")
    if summary.get("precision") != 1.0 or summary.get("recall") != 1.0 or summary.get("specificity") != 1.0:
        failures.append("Independent Discovery Challenge contains a false discovery, miss, or failed abstention")
    if not summary.get("label_firewall_verified") or not report.get("label_firewall_verified"):
        failures.append("Independent Discovery Challenge label firewall is not verified")
    for field in ("corpus_hash", "labels_hash", "source_registry_hash"):
        if not report.get(field):
            failures.append(f"Independent Discovery Challenge missing {field}")
    files = [report_path]
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        if not signed_path.is_file():
            failures.append("Signed Independent Discovery Challenge envelope is missing")
        else:
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"Independent Discovery Challenge signature: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures


def validate_preregistered_reproduction(root: Path) -> tuple[list[Path], dict, list[str]]:
    from nexus_u.benchmark.reproduction import LOCAL_EVALUATOR_SECRETS
    failures: list[str] = []
    base = root / "benchmark-results/reproduction"
    report_path = base / "preregistered-reproduction.json"
    protocol_path = base / "preregistration.json"
    bundle_manifest = base / "reproduction-bundle/MANIFEST.json"
    if not report_path.is_file():
        return [], {}, ["Preregistered Reproduction report is missing"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    if summary.get("status") != "PROCESS_REPRODUCED" or not summary.get("reproduced"):
        failures.append("Preregistered Reproduction did not reach PROCESS_REPRODUCED")
    if summary.get("evaluator_count", 0) < 3 or summary.get("evaluator_quorum", 0) < 3:
        failures.append("Preregistered Reproduction requires three evaluator replays and quorum")
    if summary.get("valid_signatures") != summary.get("evaluator_count"):
        failures.append("Not every evaluator result had a valid signature")
    if summary.get("distinct_key_ids") != summary.get("evaluator_count"):
        failures.append("Evaluator results do not use distinct key identifiers")
    for field in (
        "exact_prediction_agreement", "exact_metric_agreement", "deterministic_sampling_verified",
        "label_firewall_verified", "tamper_detection_verified", "process_isolation_verified",
    ):
        if not summary.get(field):
            failures.append(f"Preregistered Reproduction invariant failed: {field}")
    if summary.get("external_independence_claimed"):
        failures.append("Local replay benchmark must not claim external evaluator independence")
    protocol = report.get("protocol", {})
    if not protocol.get("protocol_hash") or not protocol_path.is_file():
        failures.append("Preregistration protocol or immutable hash is missing")
    if not bundle_manifest.is_file() or not report.get("replay_bundle_hash"):
        failures.append("Third-party replay bundle or hash is missing")
    files = [report_path, protocol_path, bundle_manifest]
    for envelope in report.get("evaluator_results", []):
        key_id = envelope.get("key_id")
        secret = LOCAL_EVALUATOR_SECRETS.get(str(key_id))
        if not secret:
            failures.append(f"Unknown local evaluator key: {key_id}")
            continue
        valid, errors = verify_signed_envelope(envelope, secret)
        if not valid:
            failures.extend(f"Evaluator {key_id}: {error}" for error in errors)
    for path in sorted(base.glob("*.evaluator.signed.json")):
        files.append(path)
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        for signed_name, label in (
            ("preregistration.signed.json", "Preregistration"),
            ("preregistered-reproduction.signed.json", "Reproduction aggregate"),
        ):
            signed_path = base / signed_name
            if not signed_path.is_file():
                failures.append(f"Signed {label} envelope is missing")
                continue
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"{label}: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures


def validate_lower_bound_lab(root: Path) -> tuple[list[Path], dict, list[str]]:
    failures: list[str] = []
    report_path = root / "benchmark-results/lower-bound-lab.json"
    signed_path = root / "benchmark-results/lower-bound-lab.signed.json"
    challenge_path = root / "src/nexus_u/lower_bounds/data/integer-multiplication-challenge.json"
    if not report_path.is_file():
        return [], {}, ["Lower-Bound Discovery Laboratory report is missing"]
    if not challenge_path.is_file():
        return [], {}, ["Built-in lower-bound challenge is missing"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    if summary.get("pass_rate") != 1.0:
        failures.append("Lower-Bound Laboratory benchmark did not pass every invariant")
    if summary.get("lab_false_promotions") != 0:
        failures.append("Lower-Bound Laboratory allowed an invalid proof promotion")
    if summary.get("promotion_safety_advantage", 0) < 0.8:
        failures.append("Lower-Bound Laboratory did not materially outperform the naive promotion baseline")
    lab = report.get("lab_report", {}).get("summary", {})
    if lab.get("unconditional_universal_lower_bound_status") != "OPEN":
        failures.append("The open universal lower bound was incorrectly promoted")
    if not lab.get("proved_upper_bound_present"):
        failures.append("The proved O(n log n) upper bound is missing")
    if not lab.get("matrix_transposition_route_conditional"):
        failures.append("The matrix-transposition route was not preserved as conditional")
    if not lab.get("no_false_solution_claim"):
        failures.append("The laboratory emitted a false solution claim")
    files = [report_path, challenge_path]
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        if not signed_path.is_file():
            failures.append("Signed Lower-Bound Laboratory envelope is missing")
        else:
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"Lower-Bound Laboratory signature: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures


def validate_active_lower_bound_search(root: Path) -> tuple[list[Path], dict, list[str]]:
    failures: list[str] = []
    report_path = root / "benchmark-results/active-lower-bound-search.json"
    signed_path = root / "benchmark-results/active-lower-bound-search.signed.json"
    routes_path = root / "src/nexus_u/lower_bounds/data/active-search-routes.json"
    if not report_path.is_file():
        return [], {}, ["Active Lower-Bound Search report is missing"]
    if not routes_path.is_file():
        return [], {}, ["Active lower-bound route registry is missing"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    search = report.get("search_report", {}).get("summary", {})
    if summary.get("pass_rate") != 1.0:
        failures.append("Active Lower-Bound Search benchmark did not pass every invariant")
    if summary.get("nexus_invalid_top3") != 0:
        failures.append("Active search ranked a blocked proof route in its top portfolio")
    if summary.get("naive_invalid_top3", 0) < 1:
        failures.append("Active search benchmark did not exercise the unsafe novelty baseline")
    if summary.get("search_safety_advantage", 0) < 0.8:
        failures.append("Active search did not materially outperform novelty-only ranking")
    if search.get("universal_offline_lower_bound_status") != "OPEN":
        failures.append("Active search incorrectly promoted the universal lower bound")
    if not search.get("restricted_query_certificate_valid"):
        failures.append("Restricted query lower-bound certificate failed")
    if search.get("derived_restricted_count", 0) < 1:
        failures.append("Active search produced no scoped mathematical progress")
    if search.get("formalization_ready_count", 0) < 1:
        failures.append("Active search produced no formalization-ready route")
    if not search.get("no_false_solution_claim"):
        failures.append("Active search emitted a false universal solution claim")
    files = [report_path, routes_path]
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        if not signed_path.is_file():
            failures.append("Signed Active Lower-Bound Search envelope is missing")
        else:
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"Active Lower-Bound Search signature: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures



def validate_formalized_lower_bound_search(root: Path) -> tuple[list[Path], dict, list[str]]:
    failures: list[str] = []
    report_path = root / "benchmark-results/formalized-lower-bound-search.json"
    signed_path = root / "benchmark-results/formalized-lower-bound-search.signed.json"
    lean_path = root / "benchmark-results/formalization/DecisionTreeMultiplicationTarget.lean"
    schema_path = root / "schemas/formalized-lower-bound-search.schema.json"
    if not report_path.is_file():
        return [], {}, ["Formalized Lower-Bound Search report is missing"]
    if not lean_path.is_file():
        return [], {}, ["Generated Lean formalization target is missing"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    formal = report.get("formalization_report", {}).get("summary", {})
    if summary.get("pass_rate") != 1.0:
        failures.append("Formalized lower-bound benchmark did not pass every invariant")
    if not formal.get("specialized_certificate_valid"):
        failures.append("Specialized decision-tree proof certificate failed")
    if not formal.get("all_mutations_rejected"):
        failures.append("Specialized checker did not reject every adversarial mutation")
    if formal.get("external_kernel_verified"):
        failures.append("External kernel verification was claimed without an available kernel")
    if formal.get("kernel_verified_claim_emitted"):
        failures.append("A kernel-verified claim was emitted without kernel evidence")
    if formal.get("universal_offline_lower_bound_status") != "OPEN":
        failures.append("Formalization incorrectly promoted the universal lower bound")
    if not formal.get("transposition_plan_valid"):
        failures.append("Transposition formalization obligation graph is invalid")
    if not formal.get("transposition_open_obligations"):
        failures.append("Transposition reduction open obligations were erased")
    lowered = lean_path.read_text(encoding="utf-8").lower()
    for token in ("\nsorry ", "\nadmit ", "\naxiom "):
        if token in lowered:
            failures.append(f"Lean target contains forbidden declaration: {token.strip()}")
    files = [report_path, lean_path, schema_path]
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        if not signed_path.is_file():
            failures.append("Signed Formalized Lower-Bound Search envelope is missing")
        else:
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"Formalized Lower-Bound Search signature: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures


def validate_kernel_bridge(root: Path) -> tuple[list[Path], dict, list[str]]:
    failures: list[str] = []
    report_path = root / "benchmark-results/kernel-verification-bridge.json"
    signed_path = root / "benchmark-results/kernel-verification-bridge.signed.json"
    project = root / "benchmark-results/kernel-bridge"
    lean_path = project / "NexusUKernelBridge/AllSensitive.lean"
    toolchain_path = project / "lean-toolchain"
    lakefile_path = project / "lakefile.toml"
    replay_path = project / "replay-manifest.json"
    workflow_path = project / ".github/workflows/kernel-check.yml"
    schema_path = root / "schemas/kernel-verification-bridge.schema.json"
    required = [report_path, lean_path, toolchain_path, lakefile_path, replay_path, workflow_path, schema_path]
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    if missing:
        return [], {}, [f"Kernel bridge artifact missing: {item}" for item in missing]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    bridge = report.get("bridge_report", {})
    execution = bridge.get("execution", {})
    static = bridge.get("static_checks", {})
    if summary.get("pass_rate") != 1.0:
        failures.append("Kernel bridge benchmark did not pass every invariant")
    if not static.get("passed"):
        failures.append("Kernel bridge static proof checks failed")
    if static.get("forbidden_declarations"):
        failures.append("Kernel bridge Lean source contains forbidden declarations")
    if bridge.get("universal_target_status") != "OPEN":
        failures.append("Kernel bridge incorrectly promoted the universal lower bound")
    available = bool(execution.get("available"))
    verified = bool(execution.get("verified"))
    trusted = bool(execution.get("trusted_identity"))
    if verified and not trusted:
        failures.append("Kernel verification was accepted from an untrusted toolchain identity")
    if available and trusted and not verified:
        failures.append("Pinned Lean toolchain was available but rejected the proof project")
    if not available and bridge.get("status") != "PROOF_PROJECT_READY_KERNEL_PENDING":
        failures.append("Unavailable Lean toolchain was not represented as an explicit pending status")
    if verified and bridge.get("status") != "KERNEL_VERIFIED":
        failures.append("Verified kernel execution did not produce KERNEL_VERIFIED status")
    lowered = lean_path.read_text(encoding="utf-8").lower()
    for token in ("\nsorry ", "\nadmit ", "\naxiom ", "\nunsafe "):
        if token in lowered:
            failures.append(f"Kernel bridge source contains forbidden declaration: {token.strip()}")
    if toolchain_path.read_text(encoding="utf-8").strip() != "leanprover/lean4:v4.29.1":
        failures.append("Kernel bridge toolchain pin changed")
    files = required
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        if not signed_path.is_file():
            failures.append("Signed Kernel Verification Bridge envelope is missing")
        else:
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"Kernel Verification Bridge signature: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures


def validate_cross_kernel(root: Path) -> tuple[list[Path], dict, list[str]]:
    failures: list[str] = []
    report_path = root / "benchmark-results/cross-kernel-lower-bound.json"
    signed_path = root / "benchmark-results/cross-kernel-lower-bound.signed.json"
    if not report_path.is_file():
        return [], {}, ["Cross-kernel lower-bound report is missing"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    if not summary.get("arithmetic_certificate_verified"):
        failures.append("Arithmetic sensitivity certificate failed")
    if not summary.get("logical_microkernel_verified"):
        failures.append("Logical natural-deduction microkernel failed")
    if not summary.get("logical_mutations_rejected"):
        failures.append("Logical microkernel mutation suite failed")
    if not summary.get("composed_restricted_result"):
        failures.append("Cross-kernel restricted result did not compose")
    if summary.get("restricted_status") != "CROSS_KERNEL_SCOPED_VERIFIED":
        failures.append("Cross-kernel result has an invalid scoped status")
    if summary.get("lean_kernel_verified"):
        failures.append("Cross-kernel benchmark must not impersonate Lean kernel verification")
    if summary.get("universal_offline_lower_bound_status") != "OPEN":
        failures.append("Cross-kernel benchmark incorrectly promoted the universal lower bound")
    files = [report_path]
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        if not signed_path.is_file():
            failures.append("Signed cross-kernel envelope is missing")
        else:
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"Cross-kernel signature: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures


def validate_kernel_receipts(root: Path) -> tuple[list[Path], dict, list[str]]:
    failures: list[str] = []
    report_path = root / "benchmark-results/kernel-receipt-federation.json"
    signed_path = root / "benchmark-results/kernel-receipt-federation.signed.json"
    request_path = root / "benchmark-results/kernel-receipt-request.json"
    schema_path = root / "schemas/kernel-receipt-federation.schema.json"
    required = [report_path, request_path, schema_path]
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    if missing:
        return [], {}, [f"Kernel receipt federation artifact missing: {item}" for item in missing]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    if summary.get("pass_rate") != 1.0:
        failures.append("Kernel receipt federation benchmark did not pass every invariant")
    if summary.get("quorum_status") != "LOCAL_PROCESS_QUORUM":
        failures.append("Local benchmark must remain LOCAL_PROCESS_QUORUM")
    if summary.get("external_independence_claimed"):
        failures.append("Local receipt benchmark falsely claimed external independence")
    if summary.get("theorem_status") != "KERNEL_RECEIPT_QUORUM_PENDING_EXTERNAL":
        failures.append("Kernel receipt benchmark emitted an invalid theorem status")
    if summary.get("universal_target_status") != "OPEN":
        failures.append("Kernel receipt benchmark promoted the universal lower bound")
    files = required
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        if not signed_path.is_file():
            failures.append("Signed kernel receipt federation envelope is missing")
        else:
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"Kernel receipt signature: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures


def validate_nexus_kernel(root: Path) -> tuple[list[Path], dict, list[str]]:
    failures: list[str] = []
    report_path = root / "benchmark-results/nexus-kernel-benchmark.json"
    proof_path = root / "benchmark-results/nexus-kernel-proof.json"
    signed_path = root / "benchmark-results/nexus-kernel-benchmark.signed.json"
    if not report_path.is_file() or not proof_path.is_file():
        return [], {}, ["Native NEXUS Kernel benchmark or proof bundle is missing"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    if summary.get("kernel_status") != "NEXUS_KERNEL_VERIFIED":
        failures.append("Native NEXUS Kernel did not verify its reference theorem")
    if not summary.get("all_checks_passed") or not summary.get("all_mutations_rejected"):
        failures.append("Native NEXUS Kernel checks or mutation defenses failed")
    if summary.get("axiom_count") != 0:
        failures.append("Native NEXUS Kernel reference theorem must be axiom-free")
    if summary.get("external_lean_compatible"):
        failures.append("Native NEXUS Kernel must not claim Lean compatibility")
    if summary.get("universal_offline_lower_bound_status") != "OPEN":
        failures.append("Native NEXUS Kernel promoted the open universal lower bound")
    trusted = report.get("trusted_core", {})
    if trusted.get("forbidden_dynamic_execution"):
        failures.append("Native NEXUS Kernel trusted core contains forbidden dynamic execution")
    files = [report_path, proof_path]
    secret = os.environ.get("NEXUS_U_SIGNING_KEY")
    if secret:
        if not signed_path.is_file():
            failures.append("Signed Native NEXUS Kernel envelope is missing")
        else:
            envelope = json.loads(signed_path.read_text(encoding="utf-8"))
            valid, errors = verify_signed_envelope(envelope, secret)
            if not valid:
                failures.extend(f"Native NEXUS Kernel signature: {error}" for error in errors)
            files.append(signed_path)
    return files, summary, failures

def main() -> int:
    root = Path(".")
    dist = root / "dist"
    artifacts = root / "artifacts"
    attestation_dir = dist / "attestations"
    attestation_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    packages = [
        path for path in dist.iterdir()
        if path.is_file() and path.name != "release-manifest.json"
    ] if dist.exists() else []
    if not packages:
        failures.append("No packaged distribution found")

    released: list[Path] = []
    obligation_graphs: list[Path] = []
    obligation_summaries: dict[str, dict] = {}
    obligation_metrics: dict[str, dict] = {}
    if artifacts.exists():
        for path in artifacts.glob("*.json"):
            if path.name.endswith((".audit.json", ".evidence.json", ".obligations.json")):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("released"):
                released.append(path)
                graph_name = data.get("obligation_graph_path")
                if not graph_name:
                    failures.append(f"{path.name}: missing obligation_graph_path")
                    continue
                graph_path = artifacts / graph_name
                if not graph_path.is_file():
                    failures.append(f"{path.name}: obligation graph file missing")
                    continue
                graph = load_obligation_graph(graph_path)
                valid, errors = graph.verify_conservation()
                promotion = graph.promotion_decision("RELEASED")
                if not valid:
                    failures.extend(f"{graph_path.name}: {error}" for error in errors)
                if not promotion["allowed"]:
                    failures.append(f"{graph_path.name}: release promotion obligations not satisfied")
                obligation_graphs.append(graph_path)
                obligation_summaries[path.name] = graph.summary()
                obligation_metrics[path.name] = data.get("obligation_metrics", {})
    if not released:
        failures.append("No released pipeline artifact found")

    benchmark_files, benchmark_summary, benchmark_failures = validate_benchmark(root)
    failures.extend(benchmark_failures)
    routing_files, routing_summary, routing_failures = validate_routing_benchmark(root)
    failures.extend(routing_failures)
    federation_files, federation_summary, federation_failures = validate_federation_benchmark(root)
    failures.extend(federation_failures)
    tension_files, tension_summary, tension_failures = validate_tension_benchmark(root)
    failures.extend(tension_failures)
    trial_files, trial_summary, trial_failures = validate_discovery_trials(root)
    failures.extend(trial_failures)
    external_files, external_summary, external_failures = validate_independent_challenge(root)
    failures.extend(external_failures)
    reproduction_files, reproduction_summary, reproduction_failures = validate_preregistered_reproduction(root)
    failures.extend(reproduction_failures)
    lower_bound_files, lower_bound_summary, lower_bound_failures = validate_lower_bound_lab(root)
    failures.extend(lower_bound_failures)
    active_search_files, active_search_summary, active_search_failures = validate_active_lower_bound_search(root)
    failures.extend(active_search_failures)
    formalized_files, formalized_summary, formalized_failures = validate_formalized_lower_bound_search(root)
    failures.extend(formalized_failures)
    kernel_bridge_files, kernel_bridge_summary, kernel_bridge_failures = validate_kernel_bridge(root)
    failures.extend(kernel_bridge_failures)
    cross_kernel_files, cross_kernel_summary, cross_kernel_failures = validate_cross_kernel(root)
    failures.extend(cross_kernel_failures)
    kernel_receipt_files, kernel_receipt_summary, kernel_receipt_failures = validate_kernel_receipts(root)
    failures.extend(kernel_receipt_failures)
    nexus_kernel_files, nexus_kernel_summary, nexus_kernel_failures = validate_nexus_kernel(root)
    failures.extend(nexus_kernel_failures)

    attestation_paths: dict[str, str] = {}
    for path in [*packages, *released, *obligation_graphs, *benchmark_files, *routing_files, *federation_files, *tension_files, *trial_files, *external_files, *reproduction_files, *lower_bound_files, *active_search_files, *formalized_files, *kernel_bridge_files, *cross_kernel_files, *kernel_receipt_files, *nexus_kernel_files]:
        output, errors = attest(path, attestation_dir)
        attestation_paths[path.name] = str(output)
        failures.extend(f"{path.name}: {error}" for error in errors)

    if failures:
        print(json.dumps({"release": "blocked", "failures": failures}, indent=2))
        return 2

    manifest = {
        "release": "approved",
        "version": VERSION,
        "packages": {path.name: sha256(path) for path in sorted(packages)},
        "pipeline_artifacts": {path.name: sha256(path) for path in sorted(released)},
        "obligation_graphs": {path.name: sha256(path) for path in sorted(obligation_graphs)},
        "obligation_summaries": obligation_summaries,
        "obligation_metrics": obligation_metrics,
        "reality_benchmark": {
            "summary": benchmark_summary,
            "files": {path.name: sha256(path) for path in benchmark_files},
        },
        "obligation_router_benchmark": {
            "summary": routing_summary,
            "files": {path.name: sha256(path) for path in routing_files},
        },
        "federated_evidence_benchmark": {
            "summary": federation_summary,
            "files": {path.name: sha256(path) for path in federation_files},
        },
        "tension_driven_discovery_benchmark": {
            "summary": tension_summary,
            "files": {path.name: sha256(path) for path in tension_files},
        },
        "blind_discovery_trials": {
            "summary": trial_summary,
            "files": {path.name: sha256(path) for path in trial_files},
        },
        "independent_discovery_challenge": {
            "summary": external_summary,
            "files": {path.name: sha256(path) for path in external_files},
        },
        "preregistered_reproduction": {
            "summary": reproduction_summary,
            "files": {path.name: sha256(path) for path in reproduction_files},
        },
        "lower_bound_discovery_laboratory": {
            "summary": lower_bound_summary,
            "files": {path.name: sha256(path) for path in lower_bound_files},
        },
        "active_lower_bound_search": {
            "summary": active_search_summary,
            "files": {path.name: sha256(path) for path in active_search_files},
        },
        "formalized_lower_bound_search": {
            "summary": formalized_summary,
            "files": {path.name: sha256(path) for path in formalized_files},
        },
        "kernel_verification_bridge": {
            "summary": kernel_bridge_summary,
            "files": {str(path.relative_to(root)): sha256(path) for path in kernel_bridge_files},
        },
        "cross_kernel_restricted_theorem": {
            "summary": cross_kernel_summary,
            "files": {path.name: sha256(path) for path in cross_kernel_files},
        },
        "kernel_witness_federation": {
            "summary": kernel_receipt_summary,
            "files": {str(path.relative_to(root)): sha256(path) for path in kernel_receipt_files},
        },
        "native_nexus_kernel": {
            "summary": nexus_kernel_summary,
            "files": {str(path.relative_to(root)): sha256(path) for path in nexus_kernel_files},
        },
        "attestations": attestation_paths,
        "provenance_format": {
            "statement": "https://in-toto.io/Statement/v1",
            "predicate": "https://slsa.dev/provenance/v1",
        },
        "release_invariants": [
            "No high-severity blocking obligation remains unresolved",
            "Every discharged or refuted obligation has evidence",
            "Obligation graph is acyclic and conservation-valid",
            "Artifact, audit chain, obligation graph, and benchmark are provenance-attested",
            "Reality Loop benchmark matches all expected outcomes",
            "Tests-only baseline accepts designed candidates that NEXUS-U correctly blocks",
            "Obligation Router matches all benchmark strategies and materially outperforms a static router",
            "Stagnation and human-authority escalation policies are exercised",
            "Federated approval requires independent cross-organization evidence",
            "Conflicts, security vetoes, missing authority, and missing cross-repository dependencies block promotion",
            "Tension-driven discovery requires independent contradictory evidence rather than random novelty generation",
            "Recommended experiments maximize expected information gain per declared cost and risk",
            "Observed benchmark results reduce measured tension without erasing unresolved evidence",
            "Blind corpus labels are withheld from the discovery engine and excluded from the corpus hash",
            "No-tension controls require clean abstention with zero false discoveries",
            "Every corpus-derived tension retains source and provenance identity",
            "External benchmark source snapshots, labels, and dataset registry are hashed separately",
            "Independent challenge inference is sealed before held-out labels are loaded",
            "Sampling, metrics, quorum, and evaluators are immutable before reproduction begins",
            "Blind inference runs in evaluator-specific subprocesses without label inputs",
            "Evaluator outputs require distinct signed identities and exact protocol agreement",
            "Local process reproduction is never promoted to external institutional independence",
            "Third-party replay bundles separate blind corpus from scoring labels",
            "The proved integer-multiplication upper bound and open matching lower bound remain distinct",
            "Conditional reductions never discharge their open premises",
            "Online, circuit, empirical, consensus, and information-counting evidence cannot be promoted across model or evidence boundaries",
            "Restricted lower bounds are preserved as progress without being universalized",
            "Active lower-bound routes are adversarially attacked before ranking",
            "Novelty-only routes cannot outrank model-valid obligation-reducing routes",
            "Scoped mathematical progress is preserved without promoting the open universal target",
            "Restricted symbolic certificates are never labeled kernel-verified",
            "Specialized proof certificates require adversarial mutation resistance",
            "Proof-assistant targets contain no placeholders or unreviewed axioms",
            "External kernel verification is never claimed when the toolchain is unavailable",
            "Transposition formalization preserves every open proof obligation",
            "Kernel status is emitted only after pinned-toolchain identity and successful proof-project compilation",
            "Absent external kernels remain explicit pending obligations rather than simulated verification",
            "The kernel bridge theorem remains scoped to all-sensitive deterministic path certificates",
            "The restricted theorem requires agreement between independent arithmetic and logical checkers",
            "The natural-deduction microkernel remains explicitly distinct from external Lean kernel verification",
            "Kernel receipts are bound to exact project, source, toolchain, command, executable, and environment digests",
            "Local reference receipts never claim external institutional independence",
            "Federated kernel promotion requires independent organizations, provenance groups, and externally verifiable signatures",
            "The native NEXUS Kernel verifies only its declared dependent-type calculus and never claims Lean compatibility",
            "Native kernel proof bundles are replayable, axiom-accounted, mutation-tested, and resource-bounded",
        ],
    }
    Path("dist/release-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
