from __future__ import annotations

import json
from pathlib import Path

from nexus_u.security.signing import write_signed_envelope
from nexus_u.trials import DiscoveryTrialRunner, load_trial_suite


def builtin_trial_suite_path() -> Path:
    return Path(__file__).resolve().parents[1] / "trials" / "data" / "obligation-tension-corpus.json"


def run_discovery_trials(
    suite: str | Path | None = None,
    *,
    output_dir: str | Path = "benchmark-results",
    signing_secret: str | None = None,
    key_id: str = "discovery-trials-local",
):
    path = Path(suite) if suite else builtin_trial_suite_path()
    suite_id, cases, metadata = load_trial_suite(path)
    report = DiscoveryTrialRunner().run_suite(suite_id, cases, metadata)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "discovery-trials.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    if signing_secret:
        write_signed_envelope(
            report.to_dict(),
            output / "discovery-trials.signed.json",
            key_id=key_id,
            secret=signing_secret,
        )
    return report, report_path
