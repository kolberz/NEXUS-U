import csv
import json
from pathlib import Path

from nexus_u.trials import claims_from_csv, corpus_digest, load_trial_suite


def test_corpus_digest_excludes_labels():
    suite_id, cases, _ = load_trial_suite({
        "suite_id": "x",
        "cases": [{
            "case_id": "c",
            "expectation": "NO_TENSION",
            "claims": [{
                "claim_id": "a", "statement": "A", "verdict": "SUPPORTS",
                "source_id": "s", "provenance_group": "p"
            }]
        }]
    })
    digest_a = corpus_digest(cases)
    cases[0].expectation = type(cases[0].expectation).TENSION
    digest_b = corpus_digest(cases)
    assert suite_id == "x"
    assert digest_a == digest_b


def test_claims_from_csv(tmp_path: Path):
    path = tmp_path / "claims.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "case_id", "claim_id", "statement", "verdict", "source_id", "provenance_group", "metadata"
        ])
        writer.writeheader()
        writer.writerow({
            "case_id": "c", "claim_id": "a", "statement": "A", "verdict": "SUPPORTS",
            "source_id": "s", "provenance_group": "p", "metadata": json.dumps({"x": 1})
        })
    claims = claims_from_csv(path)
    assert claims[0].metadata["x"] == 1
