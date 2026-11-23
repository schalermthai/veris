"""Portable smoke tests for the Veris Regression Author helper scripts."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def call(name, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *map(str, args)],
        capture_output=True, text=True, timeout=15
    )


class RegressionAuthorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        run = self.root / ".veris" / "stories" / "STORY-142" / "runs" / "run-0001"
        (run / "evidence").mkdir(parents=True)
        (run / "evidence" / "proof.txt").write_text("observed", encoding="utf-8")
        self.source = run / "results.json"
        self.source.write_text(json.dumps({
            "schema_version": 1,
            "story_id": "STORY-142",
            "run_id": "run-0001",
            "mode": "final",
            "overall_verdict": "verified",
            "implementation_revision": "rev-123",
            "criteria": [{"id": "AC-1", "description": "Transfer", "required": True}],
            "scenarios": [{
                "id": "S-01",
                "name": "Transfer ownership",
                "criterion_ids": ["AC-1"],
                "required": True,
                "status": "pass",
                "expected": "B owns organization",
                "actual": "B became owner",
                "independent_check": {"type": "database", "status": "pass"},
                "evidence": ["evidence/proof.txt"]
            }],
            "defects": []
        }, indent=2), encoding="utf-8")

    def scaffold(self):
        p = call("scaffold_case.py", "--root", self.root,
                 "--source", self.source, "--scenario", "S-01",
                 "--case", "org-transfer", "--suite", "organizations")
        self.assertEqual(p.returncode, 0, p.stderr)
        return self.root / ".veris" / "regression" / "cases" / "org-transfer.json"

    def ready(self, case):
        doc = json.loads(case.read_text())
        doc["status"] = "ready"
        doc["coverage"]["behaviors"] = ["organization.transfer"]
        doc["coverage"]["surfaces"] = ["web"]
        doc["test"].update({
            "file": "tests/e2e/transfer.spec.ts",
            "name": "transfers ownership",
            "framework": "playwright",
            "kind": "deterministic-e2e",
            "command": "npx playwright test tests/e2e/transfer.spec.ts",
            "surface_actions": ["initiate and accept transfer through UI"],
            "assertions": ["database owner equals recipient"],
            "cleanup": "delete isolated organization"
        })
        test_file = self.root / "tests" / "e2e" / "transfer.spec.ts"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("test('placeholder example', () => {});\n", encoding="utf-8")
        evidence = self.root / ".veris" / "regression" / "evidence" / "org-transfer"
        evidence.mkdir(parents=True)
        runs = []
        for i in (1, 2):
            relative = ".veris/regression/evidence/org-transfer/pass-%s.txt" % i
            (evidence / ("pass-%s.txt" % i)).write_text(
                "example result", encoding="utf-8"
            )
            runs.append({
                "id": "local-pass-%s" % i,
                "status": "pass",
                "revision": "rev-123",
                "command": doc["test"]["command"],
                "exit_code": 0,
                "clean_state": True,
                "evidence": [relative]
            })
        doc["execution"]["runs"] = runs
        case.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return doc

    def test_verified_source_accepted(self):
        p = call("inspect_story.py", "--root", self.root, "--source", self.source)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(json.loads(p.stdout)["eligible"])

    def test_partial_source_rejected(self):
        doc = json.loads(self.source.read_text())
        doc["overall_verdict"] = "partial"
        self.source.write_text(json.dumps(doc))
        p = call("inspect_story.py", "--root", self.root, "--source", self.source)
        self.assertEqual(p.returncode, 1)

    def test_scaffold_prevents_overwrite(self):
        self.scaffold()
        p = call("scaffold_case.py", "--root", self.root, "--source", self.source,
                 "--scenario", "S-01", "--case", "org-transfer",
                 "--suite", "organizations")
        self.assertEqual(p.returncode, 2)

    def test_draft_cannot_publish(self):
        case = self.scaffold()
        p = call("publish_catalog.py", "--root", self.root, "--case", case)
        self.assertNotEqual(p.returncode, 0)

    def test_ready_case_validates(self):
        case = self.scaffold()
        self.ready(case)
        p = call("validate_case.py", "--root", self.root, "--case", case)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(json.loads(p.stdout)["publishable"])

    def test_publish_and_prevent_duplicate(self):
        case = self.scaffold()
        self.ready(case)
        p = call("publish_catalog.py", "--root", self.root, "--case", case)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        catalog = json.loads(
            (self.root / ".veris" / "regression" / "catalog.json").read_text()
        )
        self.assertEqual(catalog["cases"][0]["id"], "org-transfer")
        p2 = call("publish_catalog.py", "--root", self.root, "--case", case)
        self.assertEqual(p2.returncode, 2)

    def test_one_pass_rejected(self):
        case = self.scaffold()
        doc = self.ready(case)
        doc["execution"]["runs"] = doc["execution"]["runs"][:1]
        case.write_text(json.dumps(doc))
        p = call("validate_case.py", "--root", self.root, "--case", case)
        self.assertEqual(p.returncode, 1)


if __name__ == "__main__":
    unittest.main()
