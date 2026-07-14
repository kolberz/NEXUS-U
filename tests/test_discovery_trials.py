from pathlib import Path

from nexus_u.benchmark.trials import builtin_trial_suite_path, run_discovery_trials
from nexus_u.trials import DiscoveryTrialRunner, load_trial_suite


def test_builtin_discovery_trials_are_blind_and_precise(tmp_path: Path):
    suite_id, cases, metadata = load_trial_suite(builtin_trial_suite_path())
    report = DiscoveryTrialRunner().run_suite(suite_id, cases, metadata)
    summary = report.summary()
    assert summary["case_count"] == 10
    assert summary["true_positives"] == 8
    assert summary["true_negatives"] == 2
    assert summary["false_positives"] == 0
    assert summary["false_negatives"] == 0
    assert summary["precision"] == 1.0
    assert summary["recall"] == 1.0
    assert summary["specificity"] == 1.0
    assert summary["kind_matches"] == 8
    assert summary["correct_abstentions"] == 2


def test_trial_report_written(tmp_path: Path):
    report, path = run_discovery_trials(output_dir=tmp_path)
    assert path.exists()
    assert report.summary()["f1"] == 1.0
    assert report.corpus_hash
