from __future__ import annotations

import json
from pathlib import Path

from nexus_u.external_challenge import (
    IndependentDiscoveryChallengeRunner,
    load_external_corpus,
    load_external_labels,
    load_source_registry,
)
from nexus_u.security.signing import write_signed_envelope


def builtin_external_data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "external_challenge" / "data"


def run_independent_challenge(
    corpus: str | Path | None = None,
    labels: str | Path | None = None,
    registry: str | Path | None = None,
    *,
    output_dir: str | Path = "benchmark-results",
    signing_secret: str | None = None,
    key_id: str = "independent-challenge-local",
):
    data = builtin_external_data_dir()
    corpus_path = Path(corpus) if corpus else data / "external-corpus.json"
    labels_path = Path(labels) if labels else data / "external-labels.json"
    registry_path = Path(registry) if registry else data / "source-registry.json"
    challenge_id, cases, metadata = load_external_corpus(corpus_path)
    heldout = load_external_labels(labels_path)
    sources, registry_metadata = load_source_registry(registry_path)
    source_dicts = [source.to_dict() for source in sources]
    report = IndependentDiscoveryChallengeRunner().run(
        challenge_id,
        cases,
        heldout,
        source_registry=source_dicts,
        metadata={
            **metadata,
            "source_registry": source_dicts,
            "source_registry_metadata": registry_metadata,
            "corpus_path": str(corpus_path),
            "labels_path": str(labels_path),
        },
    )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "independent-discovery-challenge.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    if signing_secret:
        write_signed_envelope(
            report.to_dict(),
            output / "independent-discovery-challenge.signed.json",
            key_id=key_id,
            secret=signing_secret,
        )
    return report, report_path
