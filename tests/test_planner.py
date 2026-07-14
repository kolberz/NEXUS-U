import unittest

from nexus_u.core.models import ArtifactType, TaskMode, TaskSpec
from nexus_u.orchestration.planner import build_workflow_plan


class PlannerTests(unittest.TestCase):
    def test_combined_modes_deduplicate_steps(self):
        task = TaskSpec(
            intent="combined",
            artifact_type=ArtifactType.SOFTWARE,
            modes=[TaskMode.SOFTWARE_ENGINEERING, TaskMode.FORMAL_PROOF],
        )
        plan = build_workflow_plan(task)
        self.assertIn("kernel_check", plan["steps"])
        self.assertIn("provenance", plan["steps"])
        self.assertEqual(len(plan["steps"]), len(set(plan["steps"])))


if __name__ == "__main__":
    unittest.main()
