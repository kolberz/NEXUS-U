import unittest

from nexus_u.core.audit import AuditChain
from nexus_u.core.models import StageEvent


class AuditTests(unittest.TestCase):
    def test_chain_verifies(self):
        chain = AuditChain()
        chain.append(StageEvent(stage="one", status="ok", message="first"))
        chain.append(StageEvent(stage="two", status="ok", message="second"))
        self.assertTrue(chain.verify())

    def test_tampering_detected(self):
        chain = AuditChain()
        chain.append(StageEvent(stage="one", status="ok", message="first"))
        chain.entries[0]["event"]["message"] = "tampered"
        self.assertFalse(chain.verify())


if __name__ == "__main__":
    unittest.main()
