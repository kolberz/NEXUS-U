from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nexus_u.external_challenge.io import load_external_corpus, load_external_labels, load_source_registry
from nexus_u.reproduction import PreregisteredReproductionRunner, create_preregistration
from nexus_u.reproduction.models import EvaluatorIdentity
from nexus_u.security.signing import write_signed_envelope

from .external import builtin_external_data_dir


LOCAL_EVALUATOR_SECRETS = {
    "local-replay-key-a": "nexus-u-local-replay-secret-a",
    "local-replay-key-b": "nexus-u-local-replay-secret-b",
    "local-replay-key-c": "nexus-u-local-replay-secret-c",
}


def run_preregistered_reproduction(
    corpus: str | Path | None = None,
    labels: str | Path | None = None,
    registry: str | Path | None = None,
    *,
    output_dir: str | Path = "benchmark-results/reproduction",
    seed: str = "nexus-u-v1.9-preregistered-seed",
    sample_size: int | None = None,
    signing_secret: str | None = None,
    key_id: str = "preregistered-reproduction-local",
):
    data = builtin_external_data_dir()
    corpus_path = Path(corpus) if corpus else data / "external-corpus.json"
    labels_path = Path(labels) if labels else data / "external-labels.json"
    registry_path = Path(registry) if registry else data / "source-registry.json"
    challenge_id, cases, metadata = load_external_corpus(corpus_path)
    heldout = load_external_labels(labels_path)
    sources, registry_metadata = load_source_registry(registry_path)
    source_dicts = [source.to_dict() for source in sources]
    size = sample_size or len(cases)
    evaluators = [
        EvaluatorIdentity("local-replay-a", "local-replay-key-a", "local-isolated-a"),
        EvaluatorIdentity("local-replay-b", "local-replay-key-b", "local-isolated-b"),
        EvaluatorIdentity("local-replay-c", "local-replay-key-c", "local-isolated-c"),
    ]
    protocol = create_preregistration(
        challenge_id, cases, heldout, source_dicts,
        seed=seed,
        sample_size=size,
        evaluators=evaluators,
        evaluator_quorum=3,
        metadata={
            "source_metadata": metadata,
            "registry_metadata": registry_metadata,
            "evaluation_scope": "local process-isolated reproduction; external evaluators not yet completed",
        },
    )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    protocol_path = output / "preregistration.json"
    protocol_path.write_text(json.dumps(protocol.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    if signing_secret:
        write_signed_envelope(protocol.to_dict(), output / "preregistration.signed.json", key_id=key_id, secret=signing_secret)
    evaluator_secrets = dict(LOCAL_EVALUATOR_SECRETS)
    report, report_path = PreregisteredReproductionRunner().run(
        protocol, cases, heldout, source_dicts, evaluator_secrets, output_dir=output
    )
    if signing_secret:
        write_signed_envelope(
            report.to_dict(), output / "preregistered-reproduction.signed.json",
            key_id=key_id, secret=signing_secret,
        )
    return report, report_path
