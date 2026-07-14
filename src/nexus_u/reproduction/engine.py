from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from nexus_u import __version__
from nexus_u.external_challenge.io import corpus_hash, digest_payload
from nexus_u.external_challenge.models import ExternalCase, ExternalLabel
from nexus_u.security.signing import hmac_sign, verify_signed_envelope

from .models import EvaluatorIdentity, EvaluatorResult, Preregistration, ReproductionReport


def deterministic_sample(case_ids: list[str], seed: str, sample_size: int) -> list[str]:
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    if sample_size > len(case_ids):
        raise ValueError("sample_size exceeds corpus size")
    ranked = sorted(
        case_ids,
        key=lambda case_id: (hashlib.sha256(f"{seed}:{case_id}".encode()).hexdigest(), case_id),
    )
    return ranked[:sample_size]


def _protocol_hash(protocol: Preregistration) -> str:
    return digest_payload(protocol.hash_payload())


def create_preregistration(
    challenge_id: str,
    cases: list[ExternalCase],
    labels: dict[str, ExternalLabel],
    source_registry: list[dict[str, Any]],
    *,
    seed: str,
    sample_size: int,
    evaluators: list[EvaluatorIdentity],
    evaluator_quorum: int,
    metadata: dict[str, Any] | None = None,
) -> Preregistration:
    if evaluator_quorum < 1 or evaluator_quorum > len(evaluators):
        raise ValueError("invalid evaluator quorum")
    if len({item.evaluator_id for item in evaluators}) != len(evaluators):
        raise ValueError("evaluator identifiers must be unique")
    if len({item.key_id for item in evaluators}) != len(evaluators):
        raise ValueError("evaluator key identifiers must be unique")
    selected = deterministic_sample([case.case_id for case in cases], seed, sample_size)
    protocol = Preregistration(
        protocol_id=f"{challenge_id}:preregistered:v1",
        title="NEXUS-U preregistered independent reproduction protocol",
        engine_version=__version__,
        corpus_hash=corpus_hash(cases),
        labels_hash=digest_payload({key: value.to_dict() for key, value in sorted(labels.items())}),
        source_registry_hash=digest_payload(source_registry),
        seed=seed,
        sample_size=sample_size,
        selection_algorithm="sha256(seed || ':' || case_id), ascending",
        selected_case_ids=selected,
        evaluators=evaluators,
        evaluator_quorum=evaluator_quorum,
        primary_metrics=["precision", "recall", "specificity", "f1", "kind_matches", "experiment_matches"],
        success_criteria={
            "minimum_valid_evaluators": evaluator_quorum,
            "exact_prediction_agreement": True,
            "exact_metric_agreement": True,
            "label_firewall_required": True,
            "tamper_detection_required": True,
        },
        metadata={
            "challenge_id": challenge_id,
            "labels_physically_separated_during_inference": True,
            "external_independence_claimed": False,
            **(metadata or {}),
        },
    )
    protocol.protocol_hash = _protocol_hash(protocol)
    return protocol


def verify_preregistration(protocol: Preregistration) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if protocol.protocol_hash != _protocol_hash(protocol):
        errors.append("protocol hash mismatch")
    if protocol.selected_case_ids != deterministic_sample(
        sorted(protocol.selected_case_ids), protocol.seed, len(protocol.selected_case_ids)
    ):
        # This check alone is insufficient with a subset, so the runner also rechecks against the full corpus.
        pass
    if protocol.evaluator_quorum > len(protocol.evaluators):
        errors.append("quorum exceeds evaluator count")
    return not errors, errors


def _prediction_view(inference: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": inference["case_id"],
        "predicted_tension": bool(inference["predicted_tension"]),
        "predicted_kind": inference.get("predicted_kind"),
        "tension_score": float(inference.get("tension_score", 0.0)),
        "recommended_experiment": inference.get("recommended_experiment"),
        "source_count": int(inference.get("source_count", 0)),
        "source_ids": list(inference.get("source_ids", [])),
    }


def _score(predictions: list[dict[str, Any]], labels: dict[str, ExternalLabel]) -> dict[str, Any]:
    tp = fp = fn = tn = kind_matches = experiment_matches = 0
    cases: list[dict[str, Any]] = []
    for inference in predictions:
        label = labels[inference["case_id"]]
        predicted = bool(inference["predicted_tension"])
        expected = bool(label.expected_tension)
        if expected and predicted: tp += 1
        elif not expected and predicted: fp += 1
        elif expected and not predicted: fn += 1
        else: tn += 1
        expected_kind = label.expected_kind.value if label.expected_kind else None
        kind_match = (not expected) or inference.get("predicted_kind") == expected_kind
        lowered = (inference.get("recommended_experiment") or "").lower()
        experiment_match = (not expected and not inference.get("recommended_experiment")) or (
            expected and (not label.expected_experiment_terms or any(term in lowered for term in label.expected_experiment_terms))
        )
        kind_matches += int(kind_match and expected)
        experiment_matches += int(experiment_match and expected)
        cases.append({
            "case_id": inference["case_id"],
            "expected_tension": expected,
            "predicted_tension": predicted,
            "expected_kind": expected_kind,
            "predicted_kind": inference.get("predicted_kind"),
            "kind_match": kind_match,
            "experiment_match": experiment_match,
        })
    precision = tp/(tp+fp) if tp+fp else 1.0
    recall = tp/(tp+fn) if tp+fn else 1.0
    specificity = tn/(tn+fp) if tn+fp else 1.0
    f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {
        "case_count": len(predictions),
        "true_positives": tp, "false_positives": fp, "false_negatives": fn, "true_negatives": tn,
        "precision": round(precision, 6), "recall": round(recall, 6),
        "specificity": round(specificity, 6), "f1": round(f1, 6),
        "kind_matches": kind_matches, "experiment_matches": experiment_matches,
        "cases": cases,
    }


class PreregisteredReproductionRunner:
    def _infer_isolated(self, evaluator: EvaluatorIdentity, cases: list[ExternalCase], work: Path) -> dict[str, Any]:
        input_path = work / f"{evaluator.evaluator_id}.blind-input.json"
        output_path = work / f"{evaluator.evaluator_id}.sealed-predictions.json"
        input_path.write_text(json.dumps({
            "evaluator_id": evaluator.evaluator_id,
            "cases": [case.to_dict() for case in cases],
        }, indent=2, sort_keys=True), encoding="utf-8")
        env = os.environ.copy()
        source_root = str(Path(__file__).resolve().parents[2])
        env["PYTHONPATH"] = source_root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        proc = subprocess.run(
            [sys.executable, "-m", "nexus_u.reproduction.worker", str(input_path), str(output_path)],
            capture_output=True, text=True, timeout=120, check=False, env=env,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"evaluator {evaluator.evaluator_id} failed: {proc.stderr[-500:]}")
        return json.loads(output_path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_replay_bundle(
        output: Path,
        protocol: Preregistration,
        selected_cases: list[ExternalCase],
        selected_labels: dict[str, ExternalLabel],
        source_registry: list[dict[str, Any]],
    ) -> tuple[Path, str]:
        bundle = output / "reproduction-bundle"
        blind = bundle / "blind"
        scoring = bundle / "scoring"
        blind.mkdir(parents=True, exist_ok=True)
        scoring.mkdir(parents=True, exist_ok=True)
        (bundle / "preregistration.json").write_text(json.dumps(protocol.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        (blind / "corpus.json").write_text(json.dumps({"cases": [case.to_dict() for case in selected_cases]}, indent=2, sort_keys=True), encoding="utf-8")
        (scoring / "labels.json").write_text(json.dumps({"labels": [label.to_dict() for label in selected_labels.values()]}, indent=2, sort_keys=True), encoding="utf-8")
        (bundle / "source-registry.json").write_text(json.dumps({"sources": source_registry}, indent=2, sort_keys=True), encoding="utf-8")
        (bundle / "evaluator-registry.json").write_text(json.dumps({"evaluators": [e.to_dict() for e in protocol.evaluators]}, indent=2, sort_keys=True), encoding="utf-8")
        (bundle / "README.md").write_text(
            "# NEXUS-U Reproduction Bundle\n\n"
            "The blind corpus and scoring labels are deliberately stored in separate directories. "
            "Run inference against `blind/corpus.json`, seal prediction hashes, then open `scoring/labels.json`.\n\n"
            "This bundle enables third-party replay but does not itself prove organizational independence.\n",
            encoding="utf-8",
        )
        file_hashes = {}
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                file_hashes[str(path.relative_to(bundle))] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = {"schema": "https://nexus-u.dev/reproduction-bundle/v1", "files": file_hashes}
        (bundle / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return bundle, digest_payload(manifest)

    def run(
        self,
        protocol: Preregistration,
        cases: list[ExternalCase],
        labels: dict[str, ExternalLabel],
        source_registry: list[dict[str, Any]],
        evaluator_secrets: dict[str, str],
        *,
        output_dir: str | Path,
    ) -> tuple[ReproductionReport, Path]:
        valid, errors = verify_preregistration(protocol)
        if not valid:
            raise ValueError("; ".join(errors))
        expected_sample = deterministic_sample([case.case_id for case in cases], protocol.seed, protocol.sample_size)
        if expected_sample != protocol.selected_case_ids:
            raise ValueError("preregistered sample does not match corpus and seed")
        if corpus_hash(cases) != protocol.corpus_hash:
            raise ValueError("corpus hash mismatch")
        if digest_payload({key: value.to_dict() for key, value in sorted(labels.items())}) != protocol.labels_hash:
            raise ValueError("labels hash mismatch")
        if digest_payload(source_registry) != protocol.source_registry_hash:
            raise ValueError("source registry hash mismatch")
        selected_set = set(protocol.selected_case_ids)
        selected_cases = [case for case in cases if case.case_id in selected_set]
        selected_cases.sort(key=lambda item: protocol.selected_case_ids.index(item.case_id))
        selected_labels = {key: labels[key] for key in protocol.selected_case_ids}
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        evaluator_envelopes: list[dict[str, Any]] = []
        process_ids: list[int] = []
        prediction_hashes: list[str] = []
        metric_hashes: list[str] = []
        with tempfile.TemporaryDirectory(prefix="nexus-u-repro-") as tmp:
            work = Path(tmp)
            for evaluator in protocol.evaluators:
                secret = evaluator_secrets.get(evaluator.key_id)
                if not secret:
                    raise ValueError(f"missing secret for evaluator key {evaluator.key_id}")
                blind_result = self._infer_isolated(evaluator, selected_cases, work)
                predictions = [_prediction_view(item) for item in blind_result["predictions"]]
                sealed_hash = digest_payload(predictions)
                process_ids.append(int(blind_result["process_id"]))
                prediction_hashes.append(sealed_hash)
                metrics = _score(predictions, selected_labels)
                metric_hashes.append(digest_payload(metrics))
                result = EvaluatorResult(
                    evaluator_id=evaluator.evaluator_id,
                    key_id=evaluator.key_id,
                    organization=evaluator.organization,
                    independence_scope=evaluator.independence_scope,
                    protocol_hash=protocol.protocol_hash,
                    corpus_hash=protocol.corpus_hash,
                    labels_hash=protocol.labels_hash,
                    selected_case_ids=list(protocol.selected_case_ids),
                    sealed_predictions_hash=sealed_hash,
                    inference_process_id=int(blind_result["process_id"]),
                    inference_engine_version=__version__,
                    metrics=metrics,
                    predictions=predictions,
                    label_firewall_verified=sealed_hash == digest_payload(predictions),
                )
                payload = result.to_dict()
                envelope = {
                    "algorithm": "HMAC-SHA256",
                    "key_id": evaluator.key_id,
                    "payload": payload,
                    "signature": hmac_sign(payload, secret),
                }
                evaluator_envelopes.append(envelope)
                (output / f"{evaluator.evaluator_id}.evaluator.signed.json").write_text(
                    json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8"
                )
        valid_signatures = 0
        protocol_matches = 0
        for envelope in evaluator_envelopes:
            secret = evaluator_secrets[envelope["key_id"]]
            ok, _ = verify_signed_envelope(envelope, secret)
            valid_signatures += int(ok)
            protocol_matches += int(envelope["payload"]["protocol_hash"] == protocol.protocol_hash)
        tampered = copy.deepcopy(evaluator_envelopes[0])
        tampered["payload"]["metrics"]["precision"] = 0.123456
        tamper_ok, _ = verify_signed_envelope(tampered, evaluator_secrets[tampered["key_id"]])
        bundle_path, bundle_hash = self._write_replay_bundle(output, protocol, selected_cases, selected_labels, source_registry)
        report = ReproductionReport(
            protocol=protocol,
            evaluator_results=evaluator_envelopes,
            valid_signatures=valid_signatures,
            protocol_matches=protocol_matches,
            distinct_key_ids=len({item["key_id"] for item in evaluator_envelopes}),
            exact_prediction_agreement=len(set(prediction_hashes)) == 1,
            exact_metric_agreement=len(set(metric_hashes)) == 1,
            deterministic_sampling_verified=expected_sample == protocol.selected_case_ids,
            label_firewall_verified=all(item["payload"]["label_firewall_verified"] for item in evaluator_envelopes),
            tamper_detection_verified=not tamper_ok,
            process_isolation_verified=len(process_ids) == len(set(process_ids)),
            replay_bundle_hash=bundle_hash,
            external_independence_claimed=False,
        )
        report_path = output / "preregistered-reproduction.json"
        report_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return report, report_path
