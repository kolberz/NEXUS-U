import tempfile
import unittest
from pathlib import Path

from nexus_u.core.models import ArtifactType, ResourceBudget, RunStatus, TaskMode, TaskSpec
from nexus_u.core.pipeline import Pipeline


class PipelineTests(unittest.TestCase):
    def test_python_pipeline_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = TaskSpec(
                intent="Run a release candidate",
                artifact_type=ArtifactType.SOFTWARE,
                modes=[TaskMode.SOFTWARE_ENGINEERING],
                adapter="python",
                success_conditions=["READY"],
                inputs={"code": "print('READY')"},
                budget=ResourceBudget(wall_clock_seconds=5, memory_mb=1024, output_bytes=100_000),
            )
            record, path = Pipeline(tmp).run(task)
            self.assertEqual(record.status, RunStatus.RELEASED)
            self.assertTrue(record.released)
            self.assertTrue(path.exists())

    def test_missing_success_condition_is_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = TaskSpec(
                intent="Run a failing candidate",
                artifact_type=ArtifactType.SOFTWARE,
                modes=[TaskMode.SOFTWARE_ENGINEERING],
                adapter="python",
                success_conditions=["EXPECTED"],
                inputs={"code": "print('OTHER')"},
            )
            record, _ = Pipeline(tmp).run(task)
            self.assertEqual(record.status, RunStatus.PARTIAL)
            self.assertFalse(record.released)

    def test_safety_gate_rejects(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = TaskSpec(
                intent="Reject unsafe",
                artifact_type=ArtifactType.DOCUMENT,
                modes=[TaskMode.POLICY_AND_COMPLIANCE],
                adapter="document",
                inputs={"body": "safe document", "force_safety_failure": True},
            )
            record, _ = Pipeline(tmp).run(task)
            self.assertEqual(record.status, RunStatus.REJECTED)


if __name__ == "__main__":
    unittest.main()
