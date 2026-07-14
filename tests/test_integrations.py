import unittest
from unittest.mock import patch

from nexus_u.adapters.lean import LeanAdapter
from nexus_u.adapters.registry import AdapterRegistry
from nexus_u.core.models import ArtifactType, TaskMode, TaskSpec
from nexus_u.integrations.capabilities import capability_report


class IntegrationTests(unittest.TestCase):
    def test_builtin_adapters_registered(self):
        names = AdapterRegistry(load_plugins=False).names()
        for expected in ("document", "python", "discovery", "lean", "dafny"):
            self.assertIn(expected, names)

    def test_capability_report_has_tools(self):
        report = capability_report()
        self.assertIn("runtime", report)
        self.assertIn("tools", report)

    def test_lean_rejects_placeholder(self):
        task = TaskSpec(
            intent="proof",
            artifact_type=ArtifactType.THEOREM,
            modes=[TaskMode.FORMAL_PROOF],
            adapter="lean",
            inputs={"source": "theorem x : True := by sorry"},
        )
        result = LeanAdapter().construct(task)
        self.assertFalse(result.success)

    @patch("nexus_u.adapters.lean.shutil.which", return_value=None)
    def test_lean_unavailable_is_explicit(self, _which):
        task = TaskSpec(
            intent="proof",
            artifact_type=ArtifactType.THEOREM,
            modes=[TaskMode.FORMAL_PROOF],
            adapter="lean",
            inputs={"source": "theorem x : True := by trivial"},
        )
        adapter = LeanAdapter()
        result = adapter.execute(task, adapter.construct(task))
        self.assertFalse(result.success)
        self.assertTrue(any("unavailable" in item.lower() for item in result.obligations))


if __name__ == "__main__":
    unittest.main()
