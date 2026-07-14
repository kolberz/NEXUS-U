import tempfile
import unittest

from nexus_u.core.models import ArtifactType, TaskMode, TaskSpec
from nexus_u.core.pipeline import Pipeline
from nexus_u.core.policy import PolicyEngine


class PolicyTests(unittest.TestCase):
    def test_high_risk_requires_approval(self):
        task = TaskSpec(
            intent="high risk",
            artifact_type=ArtifactType.SOFTWARE,
            modes=[TaskMode.SOFTWARE_ENGINEERING],
            adapter="python",
            success_conditions=["READY"],
            inputs={"code": "print('READY')", "high_risk": True},
        )
        decision = PolicyEngine().evaluate_preflight(task, ["python"])
        self.assertFalse(decision.allowed)
        self.assertIn("safety_owner", decision.required_approvals)

    def test_high_risk_approval_allows_pipeline(self):
        task = TaskSpec(
            intent="approved high risk",
            artifact_type=ArtifactType.SOFTWARE,
            modes=[TaskMode.SOFTWARE_ENGINEERING],
            adapter="python",
            success_conditions=["READY"],
            assumptions=["Approved isolated execution"],
            inputs={
                "code": "print('READY')",
                "high_risk": True,
                "approvals": [{"role": "safety_owner", "approver": "reviewer"}],
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            record, path = Pipeline(tmp).run(task)
            self.assertTrue(record.released)
            self.assertTrue((path.parent / record.evidence_bundle).exists())
            self.assertEqual(record.policy_decisions[-1]["phase"], "release")


if __name__ == "__main__":
    unittest.main()
