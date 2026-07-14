import tempfile
import time
import unittest
from pathlib import Path

from nexus_u.jobs.manager import JobManager
from nexus_u.storage.sqlite import ControlStore


class StorageJobTests(unittest.TestCase):
    def test_async_job_persists_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ControlStore(Path(tmp) / "control.db")
            manager = JobManager(store, workers=1)
            job_id = manager.submit({
                "intent": "job",
                "artifact_type": "software",
                "modes": ["SOFTWARE_ENGINEERING"],
                "adapter": "python",
                "success_conditions": ["READY"],
                "assumptions": ["trusted local execution"],
                "inputs": {"code": "print('READY')"},
            })
            deadline = time.time() + 10
            job = None
            while time.time() < deadline:
                job = store.get_job(job_id)
                if job and job["status"] not in {"QUEUED", "RUNNING"}:
                    break
                time.sleep(0.05)
            self.assertIsNotNone(job)
            self.assertEqual(job["status"], "SUCCEEDED")
            self.assertIsNotNone(store.get_artifact(job["artifact_id"]))


if __name__ == "__main__":
    unittest.main()
