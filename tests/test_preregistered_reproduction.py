from __future__ import annotations

import copy
import json
from pathlib import Path

from nexus_u.benchmark.external import builtin_external_data_dir
from nexus_u.benchmark.reproduction import run_preregistered_reproduction
from nexus_u.external_challenge.io import load_external_corpus, load_external_labels, load_source_registry
from nexus_u.reproduction import create_preregistration, deterministic_sample
from nexus_u.reproduction.models import EvaluatorIdentity


def _inputs():
    data = builtin_external_data_dir()
    challenge_id, cases, metadata = load_external_corpus(data / "external-corpus.json")
    labels = load_external_labels(data / "external-labels.json")
    sources, _ = load_source_registry(data / "source-registry.json")
    return challenge_id, cases, labels, [item.to_dict() for item in sources], metadata


def test_deterministic_sample_is_stable_and_seeded():
    ids = ["a", "b", "c", "d", "e"]
    first = deterministic_sample(ids, "seed-a", 3)
    assert first == deterministic_sample(list(reversed(ids)), "seed-a", 3)
    assert first != deterministic_sample(ids, "seed-b", 3)


def test_preregistration_hash_detects_mutation():
    challenge_id, cases, labels, sources, metadata = _inputs()
    evaluators = [EvaluatorIdentity("e1", "k1", "o1")]
    protocol = create_preregistration(
        challenge_id, cases, labels, sources, seed="s", sample_size=4,
        evaluators=evaluators, evaluator_quorum=1, metadata=metadata,
    )
    original = protocol.protocol_hash
    protocol.seed = "changed"
    from nexus_u.reproduction.engine import verify_preregistration
    valid, errors = verify_preregistration(protocol)
    assert not valid
    assert errors
    assert protocol.protocol_hash == original


def test_process_isolated_reproduction_and_bundle(tmp_path: Path):
    report, path = run_preregistered_reproduction(output_dir=tmp_path, sample_size=8)
    summary = report.summary()
    assert path.is_file()
    assert summary["reproduced"] is True
    assert summary["status"] == "PROCESS_REPRODUCED"
    assert summary["evaluator_count"] == 3
    assert summary["valid_signatures"] == 3
    assert summary["exact_prediction_agreement"] is True
    assert summary["label_firewall_verified"] is True
    assert summary["tamper_detection_verified"] is True
    assert summary["external_independence_claimed"] is False
    assert (tmp_path / "reproduction-bundle" / "blind" / "corpus.json").is_file()
    assert (tmp_path / "reproduction-bundle" / "scoring" / "labels.json").is_file()
    assert (tmp_path / "reproduction-bundle" / "MANIFEST.json").is_file()


def test_reproduction_predictions_ignore_label_mutation(tmp_path: Path):
    report, _ = run_preregistered_reproduction(output_dir=tmp_path / "one", sample_size=8)
    hashes = [item["payload"]["sealed_predictions_hash"] for item in report.evaluator_results]
    assert len(set(hashes)) == 1
    # Labels affect scoring, never the already-sealed prediction hashes.
    mutated = copy.deepcopy(report.evaluator_results[0]["payload"])
    mutated["metrics"]["precision"] = 0.0
    assert mutated["sealed_predictions_hash"] == hashes[0]


def test_reproduction_report_round_trip(tmp_path: Path):
    report, path = run_preregistered_reproduction(output_dir=tmp_path, sample_size=8)
    raw = json.loads(path.read_text())
    assert raw["protocol"]["protocol_hash"] == report.protocol.protocol_hash
    assert raw["summary"]["reproduced"] is True
