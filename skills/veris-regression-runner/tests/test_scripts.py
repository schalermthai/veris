"""Offline tests of runner result rules and safe command mapping."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
CORE = SKILL / "scripts" / "_core.py"
EXEC = SKILL / "scripts" / "execute_tests.py"

def load_module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, str(SKILL / "scripts"))
        cls.core = load_module("vrr_core", CORE)
        cls.executor = load_module("vrr_exec", EXEC)

    def test_command_adapter_does_not_use_raw_catalog_command(self):
        case = {"id": "transfer", "test_file": "tests/e2e/transfer.spec.ts"}
        metadata = {
            "test": {
                "file": "tests/e2e/transfer.spec.ts",
                "framework": "playwright",
                "kind": "deterministic-e2e",
                "command": "echo UNSAFE",
            }
        }
        runtime = {"allowed_executables": ["playwright"]}
        policy = {"test_adapters": {
            "playwright": {"enabled": True, "executable": "playwright"}
        }}
        command = self.core.commands_for(case, metadata, runtime, policy)
        self.assertEqual(command, [
            "playwright", "test",
            "tests/e2e/transfer.spec.ts", "--reporter=json"
        ])
        self.assertNotIn("UNSAFE", str(command))

    def test_agentic_test_not_silently_executed(self):
        case = {"id": "t", "test_file": "tests/e2e/t.spec.ts"}
        metadata = {"test": {"file": case["test_file"],
                              "framework": "playwright",
                              "kind": "agentic-e2e"}}
        with self.assertRaises(ValueError):
            self.core.commands_for(case, metadata,
                {"allowed_executables": ["playwright"]},
                {"test_adapters": {"playwright": {
                    "enabled": True, "executable": "playwright"
                }}})

    def test_verdict_not_run_is_blocked(self):
        self.assertEqual(
            self.core.computed_verdict([
                {"status": "pass"}, {"status": "not_run"}
            ]), "blocked"
        )

    def test_verdict_failed_requires_confirmed_fail(self):
        self.assertEqual(self.core.computed_verdict([
            {"status": "pass"}, {"status": "inconclusive"}
        ]), "inconclusive")
        self.assertEqual(self.core.computed_verdict([
            {"status": "pass"}, {"status": "fail"}
        ]), "failed")

    def test_playwright_valid_json_result(self):
        good = json.dumps({"stats": {
            "expected": 2, "unexpected": 0,
            "skipped": 0, "flaky": 0
        }, "errors": []})
        state, _ = self.executor.interpret("playwright", good, 0)
        self.assertEqual(state, "pass")

    def test_playwright_zero_test_does_not_pass(self):
        empty = json.dumps({"stats": {
            "expected": 0, "unexpected": 0,
            "skipped": 0, "flaky": 0
        }, "errors": []})
        state, _ = self.executor.interpret("playwright", empty, 0)
        self.assertNotEqual(state, "pass")

    def test_pytest_zero_tests_is_not_pass(self):
        self.assertNotEqual(
            self.executor.interpret("pytest", "no tests ran", 0)[0],
            "pass"
        )

    def test_summary_counts(self):
        stats = self.core.summary([
            {"status": "pass"}, {"status": "blocked"},
            {"status": "inconclusive"}
        ])
        self.assertEqual(stats["selected"], 3)
        self.assertEqual(stats["passed"], 1)
        self.assertEqual(stats["blocked"], 1)


if __name__ == "__main__":
    unittest.main()
