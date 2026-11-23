"""Lightweight smoke tests for Veris scripts (standard library only)."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SCRIPTS = HERE / "scripts"


def run_script(name, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *map(str, args)],
        capture_output=True, text=True, timeout=15
    )


class VerisScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        veris = self.root / ".veris"
        veris.mkdir()
        (veris / "verification-profile.yaml").write_text(
            "schema_version: 1\nbootstrap:\n  status: ready\n"
            "handoff:\n  story_verifier_ready: true\n",
            encoding="utf-8"
        )
        (veris / "verification-playbook.md").write_text(
            "# Test playbook\n", encoding="utf-8"
        )
        (veris / "bootstrap-report.md").write_text(
            "# Bootstrap report\n", encoding="utf-8"
        )

    def init(self, mode="final"):
        process = run_script(
            "init_run.py", "--root", self.root,
            "--story", "STORY-142", "--mode", mode,
            "--ac", "AC-1=Transfer ownership"
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        return Path(result["results"])

    def passing(self, path):
        doc = json.loads(path.read_text())
        doc["implementation_revision"] = "fixture-revision"
        doc["overall_verdict"] = "verified"
        evidence = path.parent / "evidence" / "proof.txt"
        evidence.write_text("Observed UI and state.", encoding="utf-8")
        doc["scenarios"] = [{
            "id": "S-01",
            "name": "Transfer ownership",
            "criterion_ids": ["AC-1"],
            "required": True,
            "status": "pass",
            "expected": "Transferred",
            "actual": "Recipient became owner",
            "independent_check": {
                "type": "database",
                "status": "pass",
                "notes": "Owner ID checked"
            },
            "evidence": ["evidence/proof.txt"],
            "defects": [],
            "limitations": []
        }]
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return doc

    def test_context_ready(self):
        p = run_script("check_context.py", "--root", self.root, "--strict")
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.loads(p.stdout)
        self.assertEqual(data["bootstrap_status"], "ready")

    def test_init_does_not_overwrite(self):
        first = self.init()
        second = self.init()
        self.assertNotEqual(first.parent, second.parent)
        self.assertTrue(first.is_file())
        self.assertTrue(second.is_file())

    def test_pass_with_evidence(self):
        path = self.init()
        self.passing(path)
        p = run_script("validate_results.py", path)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)["computed_verdict"], "verified")

    def test_missing_evidence_rejected(self):
        path = self.init()
        self.passing(path)
        (path.parent / "evidence" / "proof.txt").unlink()
        p = run_script("validate_results.py", path)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertFalse(json.loads(p.stdout)["valid"])

    def test_verdict_mismatch_rejected(self):
        path = self.init()
        doc = self.passing(path)
        doc["overall_verdict"] = "blocked"
        path.write_text(json.dumps(doc), encoding="utf-8")
        p = run_script("validate_results.py", path)
        self.assertEqual(p.returncode, 1, p.stdout)

    def test_retest_comparison(self):
        first = self.init()
        self.passing(first)
        second = self.init("retest")
        doc = json.loads(second.read_text())
        doc["implementation_revision"] = "fixture-revision-2"
        doc["overall_verdict"] = "failed"
        doc["scenarios"] = [{
            "id": "S-01", "name": "Transfer ownership",
            "criterion_ids": ["AC-1"], "required": True,
            "status": "fail", "expected": "Transferred",
            "actual": "Transfer rejected",
            "independent_check": {"type": "database", "status": "fail"},
            "evidence": [], "defects": [], "limitations": []
        }]
        second.write_text(json.dumps(doc), encoding="utf-8")
        p = run_script("compare_runs.py", first, second)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)["regressed"], ["S-01"])

    def test_unrun_is_not_regression(self):
        first = self.init()
        self.passing(first)
        second = self.init("retest")
        p = run_script("compare_runs.py", first, second)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(
            json.loads(p.stdout)["previously_passing_not_retested"],
            ["S-01"]
        )


if __name__ == "__main__":
    unittest.main()
