import unittest

from nexus_u.core.models import RunStatus
from nexus_u.core.state_machine import InvalidTransition, transition


class StateMachineTests(unittest.TestCase):
    def test_valid_transition(self):
        self.assertEqual(transition(RunStatus.INTAKE, RunStatus.INTENT_COMPILED), RunStatus.INTENT_COMPILED)

    def test_invalid_transition(self):
        with self.assertRaises(InvalidTransition):
            transition(RunStatus.INTAKE, RunStatus.RELEASED)


if __name__ == "__main__":
    unittest.main()
