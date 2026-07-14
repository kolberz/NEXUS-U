from __future__ import annotations

from nexus_u.benchmark.external import builtin_external_data_dir, run_independent_challenge
from nexus_u.external_challenge import (
    IndependentDiscoveryChallengeRunner,
    load_external_corpus,
    load_external_labels,
    load_source_registry,
)


def test_independent_challenge_external_sources_and_abstention(tmp_path):
    report, path = run_independent_challenge(output_dir=tmp_path, signing_secret="secret")
    summary = report.summary()
    assert path.is_file()
    assert summary["case_count"] == 8
    assert summary["external_sources"] == 3
    assert summary["true_positives"] == 3
    assert summary["correct_abstentions"] == 5
    assert summary["false_positives"] == 0
    assert summary["false_negatives"] == 0
    assert summary["label_firewall_verified"] is True
    assert (tmp_path / "independent-discovery-challenge.signed.json").is_file()


def test_labels_do_not_enter_inference():
    data = builtin_external_data_dir()
    _, cases, _ = load_external_corpus(data / "external-corpus.json")
    labels = load_external_labels(data / "external-labels.json")
    runner = IndependentDiscoveryChallengeRunner()
    before = [(item["case_id"], item["predicted_tension"], item["predicted_kind"]) for item in [runner.infer(case) for case in cases]]
    for label in labels.values():
        label.expected_tension = not label.expected_tension
    after = [(item["case_id"], item["predicted_tension"], item["predicted_kind"]) for item in [runner.infer(case) for case in cases]]
    assert before == after


def test_source_registry_has_attribution_and_license():
    sources, metadata = load_source_registry(builtin_external_data_dir() / "source-registry.json")
    assert len(sources) == 3
    assert metadata["registry_version"] == "1.0"
    assert all(source.homepage.startswith("https://") for source in sources)
    assert all(source.citation for source in sources)
    assert all(source.license for source in sources)
