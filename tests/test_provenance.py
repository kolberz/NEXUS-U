import json
import tempfile
import unittest
from pathlib import Path

from nexus_u.provenance.attestation import build_provenance_statement, verify_provenance_statement


class ProvenanceTests(unittest.TestCase):
    def test_round_trip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = Path(tmp) / "artifact.bin"
            subject.write_bytes(b"release")
            statement = build_provenance_statement(subject)
            valid, errors = verify_provenance_statement(statement, subject)
            self.assertTrue(valid, errors)
            subject.write_bytes(b"tampered")
            valid, errors = verify_provenance_statement(statement, subject)
            self.assertFalse(valid)
            self.assertIn("Subject digest mismatch", errors)

    def test_statement_is_json_serializable(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = Path(tmp) / "artifact.bin"
            subject.write_bytes(b"release")
            json.dumps(build_provenance_statement(subject))


if __name__ == "__main__":
    unittest.main()
