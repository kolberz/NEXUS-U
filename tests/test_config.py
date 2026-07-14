import json
import tempfile
import unittest
from pathlib import Path

from nexus_u.config import ConfigError, load_task


class ConfigTests(unittest.TestCase):
    def test_load_valid_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task.json"
            path.write_text(json.dumps({
                "intent": "demo",
                "artifact_type": "document",
                "modes": ["SYSTEM_ARCHITECTURE"]
            }))
            task = load_task(path)
            self.assertEqual(task.intent, "demo")

    def test_missing_required_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task.json"
            path.write_text("{}")
            with self.assertRaises(ConfigError):
                load_task(path)


if __name__ == "__main__":
    unittest.main()
