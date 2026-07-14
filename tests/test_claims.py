import unittest

from nexus_u.core.claims import assign_status
from nexus_u.core.models import Claim, EpistemicStatus, Evidence


class ClaimTests(unittest.TestCase):
    def test_evidence_caps_claim(self):
        claim = Claim(
            statement="A theorem",
            requested_status=EpistemicStatus.KERNEL_VERIFIED,
            evidence=[Evidence(kind="execution", summary="ran")],
        )
        self.assertEqual(assign_status(claim), EpistemicStatus.EXECUTION_VERIFIED)
        self.assertTrue(claim.missing_obligations)

    def test_kernel_evidence_allows_kernel_status(self):
        claim = Claim(
            statement="A theorem",
            requested_status=EpistemicStatus.KERNEL_VERIFIED,
            evidence=[Evidence(kind="kernel", summary="kernel accepted")],
        )
        self.assertEqual(assign_status(claim), EpistemicStatus.KERNEL_VERIFIED)


if __name__ == "__main__":
    unittest.main()
