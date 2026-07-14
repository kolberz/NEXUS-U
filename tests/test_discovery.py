import tempfile
import unittest

from nexus_u.core.models import ArtifactType, RunStatus, TaskMode, TaskSpec
from nexus_u.core.pipeline import Pipeline


class DiscoveryTests(unittest.TestCase):
    def test_discovery_selects_feasible_winner(self):
        task = TaskSpec(
            intent="select",
            artifact_type=ArtifactType.EXPERIMENT,
            modes=[TaskMode.EXPERIMENTAL_RESEARCH],
            adapter="discovery",
            inputs={
                "weights": {"utility": 1, "risk": -2},
                "constraints": {"risk": {"max": 0.2}},
                "minimum_score": 1,
                "candidates": [
                    {"id": "unsafe", "metrics": {"utility": 10, "risk": 0.9}},
                    {"id": "safe", "metrics": {"utility": 5, "risk": 0.1}},
                ],
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            record, _ = Pipeline(tmp).run(task)
        self.assertEqual(record.status, RunStatus.RELEASED)
        self.assertEqual(record.output["discovery"]["winner"]["candidate_id"], "safe")
        self.assertEqual(str(record.claims[0].assigned_status), "COMPUTATIONAL_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
