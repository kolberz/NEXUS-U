import json
import tempfile
import unittest
from pathlib import Path

from nexus_u.security.signing import verify_signed_envelope, write_signed_envelope


class SigningTests(unittest.TestCase):
    def test_signed_envelope_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_signed_envelope({"claim": "ok"}, Path(tmp) / "bundle.json", key_id="test", secret="secret")
            envelope = json.loads(path.read_text())
            valid, errors = verify_signed_envelope(envelope, "secret")
            self.assertTrue(valid, errors)
            envelope["payload"]["claim"] = "tampered"
            valid, errors = verify_signed_envelope(envelope, "secret")
            self.assertFalse(valid)
            self.assertIn("Signature mismatch", errors)


if __name__ == "__main__":
    unittest.main()
