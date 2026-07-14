from __future__ import annotations

import json
from pathlib import Path

BUILTIN_SUITE = {'suite': 'nexus-u-reality-loop-v1',
 'cases': [{'id': 'good_delivery',
            'expected_baseline': True,
            'expected_nexus': True,
            'task': {'artifact_type': 'software',
                     'modes': ['SOFTWARE_ENGINEERING'],
                     'adapter': 'git_delivery',
                     'success_conditions': ['All declared Git delivery checks pass'],
                     'assumptions': ['The fixture repository is trusted local code'],
                     'budget': {'wall_clock_seconds': 20, 'memory_mb': 512, 'output_bytes': 1000000},
                     'intent': 'Add multiplication without breaking addition',
                     'inputs': {'test_commands': ['python -m unittest discover -s tests -v'],
                                'security_commands': [],
                                'build_commands': ['python -m compileall -q .'],
                                'required_paths': ['calc.py', 'tests/test_calc.py'],
                                'repository': '../fixtures/good',
                                'changes': {'calc.py': 'def add(a: int, b: int) -> int:\n'
                                                       '    return a + b\n'
                                                       '\n'
                                                       'def multiply(a: int, b: int) -> int:\n'
                                                       '    return a * b\n'},
                                'required_patterns': [{'path': 'calc.py', 'pattern': 'def multiply'}],
                                'forbidden_patterns': [{'path': 'calc.py', 'pattern': 'eval('}],
                                'rollback_required': True,
                                'rollback_command': 'git reset --hard HEAD'}}},
           {'id': 'hidden_security_violation',
            'expected_baseline': True,
            'expected_nexus': False,
            'task': {'artifact_type': 'software',
                     'modes': ['SOFTWARE_ENGINEERING'],
                     'adapter': 'git_delivery',
                     'success_conditions': ['All declared Git delivery checks pass'],
                     'assumptions': ['The fixture repository is trusted local code'],
                     'budget': {'wall_clock_seconds': 20, 'memory_mb': 512, 'output_bytes': 1000000},
                     'intent': 'Add expression evaluation while preserving existing behavior',
                     'inputs': {'test_commands': ['python -m unittest discover -s tests -v'],
                                'security_commands': [],
                                'build_commands': ['python -m compileall -q .'],
                                'required_paths': ['calc.py', 'tests/test_calc.py'],
                                'repository': '../fixtures/security',
                                'changes': {'calc.py': 'def add(a: int, b: int) -> int:\n'
                                                       '    return a + b\n'
                                                       '\n'
                                                       'def evaluate(expression: str):\n'
                                                       '    return eval(expression)\n'},
                                'forbidden_patterns': [{'path': 'calc.py', 'pattern': 'eval('}],
                                'rollback_required': True,
                                'rollback_command': 'git reset --hard HEAD'}}},
           {'id': 'missing_rollback',
            'expected_baseline': True,
            'expected_nexus': False,
            'task': {'artifact_type': 'software',
                     'modes': ['SOFTWARE_ENGINEERING'],
                     'adapter': 'git_delivery',
                     'success_conditions': ['All declared Git delivery checks pass'],
                     'assumptions': ['The fixture repository is trusted local code'],
                     'budget': {'wall_clock_seconds': 20, 'memory_mb': 512, 'output_bytes': 1000000},
                     'intent': 'Add multiplication with a production rollback contract',
                     'inputs': {'test_commands': ['python -m unittest discover -s tests -v'],
                                'security_commands': [],
                                'build_commands': ['python -m compileall -q .'],
                                'required_paths': ['calc.py', 'tests/test_calc.py'],
                                'repository': '../fixtures/rollback',
                                'changes': {'calc.py': 'def add(a: int, b: int) -> int:\n'
                                                       '    return a + b\n'
                                                       '\n'
                                                       'def multiply(a: int, b: int) -> int:\n'
                                                       '    return a * b\n'},
                                'required_patterns': [{'path': 'calc.py', 'pattern': 'def multiply'}],
                                'rollback_required': True}}},
           {'id': 'intent_drift',
            'expected_baseline': True,
            'expected_nexus': False,
            'task': {'artifact_type': 'software',
                     'modes': ['SOFTWARE_ENGINEERING'],
                     'adapter': 'git_delivery',
                     'success_conditions': ['All declared Git delivery checks pass'],
                     'assumptions': ['The fixture repository is trusted local code'],
                     'budget': {'wall_clock_seconds': 20, 'memory_mb': 512, 'output_bytes': 1000000},
                     'intent': 'Add multiplication while preserving addition',
                     'inputs': {'test_commands': ['python -m unittest discover -s tests -v'],
                                'security_commands': [],
                                'build_commands': ['python -m compileall -q .'],
                                'required_paths': ['calc.py', 'tests/test_calc.py'],
                                'repository': '../fixtures/intent',
                                'changes': {'calc.py': 'def add(a: int, b: int) -> int:\n'
                                                       '    return a + b\n'
                                                       '\n'
                                                       '# Documentation-only change\n'},
                                'required_patterns': [{'path': 'calc.py', 'pattern': 'def multiply'}],
                                'rollback_required': False}}}]}

def write_builtin_reality_suite(root: str | Path) -> Path:
    root = Path(root)
    fixtures = root / "fixtures"
    cases_dir = root / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    base_calc = "def add(a: int, b: int) -> int:\n    return a + b\n"
    tests = """import unittest\nfrom calc import add\n\nclass CalcTests(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\nif __name__ == '__main__':\n    unittest.main()\n"""
    for name in ("good", "security", "rollback", "intent"):
        target = fixtures / name
        (target / "tests").mkdir(parents=True, exist_ok=True)
        (target / "calc.py").write_text(base_calc, encoding="utf-8")
        (target / "tests/test_calc.py").write_text(tests, encoding="utf-8")
    path = cases_dir / "reality_suite.json"
    path.write_text(json.dumps(BUILTIN_SUITE, indent=2), encoding="utf-8")
    return path
