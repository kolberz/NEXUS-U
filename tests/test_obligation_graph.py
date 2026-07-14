import tempfile
import unittest
from pathlib import Path

from nexus_u.core.models import ArtifactType, Evidence, ResourceBudget, RunStatus, TaskMode, TaskSpec
from nexus_u.core.obligation_graph import (
    ObligationGraph,
    ObligationGraphError,
    ObligationKind,
    ObligationStatus,
    Relation,
    Severity,
    load_obligation_graph,
)
from nexus_u.core.pipeline import Pipeline
from nexus_u.storage.sqlite import ControlStore


class ObligationGraphTests(unittest.TestCase):
    def test_discharge_requires_evidence(self):
        graph = ObligationGraph()
        obligation = graph.add_node("Prove the claim", kind=ObligationKind.CLAIM)
        with self.assertRaises(ObligationGraphError):
            graph.discharge(obligation, [])
        evidence = graph.add_evidence(Evidence(kind="kernel", summary="Kernel accepted proof"))
        graph.discharge(obligation, [evidence])
        self.assertEqual(graph.nodes[obligation].status, ObligationStatus.DISCHARGED)
        valid, errors = graph.verify_conservation()
        self.assertTrue(valid, errors)

    def test_cycle_is_rejected(self):
        graph = ObligationGraph()
        a = graph.add_node("A")
        b = graph.add_node("B")
        graph.add_edge(a, b, Relation.DEPENDS_ON)
        with self.assertRaises(ObligationGraphError):
            graph.add_edge(b, a, Relation.DEPENDS_ON)

    def test_transfer_preserves_original_node(self):
        graph = ObligationGraph()
        original = graph.add_node("Original theorem", kind=ObligationKind.CLAIM)
        transformed = graph.transfer(original, "Equivalent normalized theorem", reason="Library alignment")
        self.assertIn(original, graph.nodes)
        self.assertIn(transformed, graph.nodes)
        self.assertEqual(graph.nodes[original].status, ObligationStatus.TRANSFERRED)
        valid, errors = graph.verify_conservation()
        self.assertTrue(valid, errors)

    def test_high_blocker_prevents_release(self):
        graph = ObligationGraph()
        graph.add_node("Unresolved safety property", kind=ObligationKind.SAFETY, severity=Severity.CRITICAL)
        graph.add_evidence(Evidence(kind="execution", summary="Something ran"))
        decision = graph.promotion_decision("RELEASED")
        self.assertFalse(decision["allowed"])
        self.assertEqual(len(decision["blocking_obligations"]), 1)

    def test_round_trip(self):
        graph = ObligationGraph()
        obligation = graph.add_node("Test round trip", kind=ObligationKind.TEST)
        evidence = graph.add_evidence(Evidence(kind="execution", summary="Test passed"))
        graph.discharge(obligation, [evidence])
        with tempfile.TemporaryDirectory() as tmp:
            path = graph.write(Path(tmp) / "graph.json")
            loaded = load_obligation_graph(path)
            self.assertEqual(loaded.sha256(), graph.sha256())
            self.assertTrue(loaded.verify_conservation()[0])

    def test_pipeline_persists_release_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = TaskSpec(
                intent="Produce obligation-aware release",
                artifact_type=ArtifactType.SOFTWARE,
                modes=[TaskMode.SOFTWARE_ENGINEERING],
                adapter="python",
                success_conditions=["READY"],
                inputs={"code": "print('READY')"},
                budget=ResourceBudget(wall_clock_seconds=5, memory_mb=1024, output_bytes=100_000),
            )
            record, _ = Pipeline(tmp).run(task)
            self.assertEqual(record.status, RunStatus.RELEASED)
            self.assertTrue(record.obligation_summary["conservation_valid"])
            self.assertEqual(record.obligation_summary["blocking_unresolved_count"], 0)
            self.assertTrue((Path(tmp) / record.obligation_graph_path).exists())

    def test_storage_indexes_obligations(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ControlStore(Path(tmp) / "control.db")
            task = TaskSpec(
                intent="Index obligations",
                artifact_type=ArtifactType.DOCUMENT,
                modes=[TaskMode.POLICY_AND_COMPLIANCE],
                adapter="document",
                success_conditions=["READY"],
                inputs={"body": "READY"},
            )
            record, _ = Pipeline(Path(tmp) / "artifacts", store=store).run(task)
            rows = store.list_obligations(artifact_id=record.artifact_id, limit=1000)
            self.assertGreater(len(rows), 0)
            self.assertIsNotNone(store.get_obligation_graph(record.artifact_id))


if __name__ == "__main__":
    unittest.main()
