"""Offline helper tests. These do not call Jev or execute E2E tests."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def run(name, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *map(str, args)],
        capture_output=True, text=True, timeout=20
    )


class SelectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        reg = self.root / ".veris" / "regression"
        (reg / "cases").mkdir(parents=True)
        self.catalog = reg / "catalog.json"
        self.policy = reg / "selection-policy.json"
        cases = []
        for cid, risk, suite in [
            ("auth-login", "high", "auth"),
            ("org-transfer", "medium", "organizations")
        ]:
            path = self.root / "tests" / (cid + ".spec.ts")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("// test fixture", encoding="utf-8")
            meta = reg / "cases" / (cid + ".json")
            meta.write_text(json.dumps({
                "id": cid, "status": "ready",
                "test": {"file": str(path.relative_to(self.root))},
                "coverage": {"suite": suite}
            }), encoding="utf-8")
            cases.append({
                "id": cid,
                "suite": suite, "risk": risk,
                "test_file": str(path.relative_to(self.root)),
                "metadata_path": str(meta.relative_to(self.root)),
                "behaviors": [cid], "components": [],
                "api_routes": [], "surfaces": ["web"]
            })
        self.catalog.write_text(json.dumps({
            "schema_version": 1, "cases": cases
        }), encoding="utf-8")
        self.policy.write_text(json.dumps({
            "schema_version": 1,
            "always_run_case_ids": ["auth-login"],
            "mandatory_rules": [],
            "cross_cutting_path_globs": [],
            "selection_limits": {"max_changed_files_for_targeted": 40}
        }), encoding="utf-8")
        self.changes = reg / "changes.json"
        self.changes.write_text(json.dumps({
            "schema_version": 1, "change_id": "PR-1",
            "base_revision": "aaa", "head_revision": "bbb",
            "diff_sha256": "hash-example",
            "changed_files": ["src/organization.ts"],
            "diff_truncated": False
        }), encoding="utf-8")
        self.impact = reg / "impact.json"

    def build(self, assessments):
        self.impact.write_text(json.dumps({
            "change_id": "PR-1", "provider": "fixture",
            "assessments": assessments, "coverage_gaps": []
        }), encoding="utf-8")
        output = self.root / ".veris" / "regression" / "selection.json"
        p = run("build_selection.py", "--root", self.root,
                "--changes", self.changes, "--impact", self.impact,
                "--out", output)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return output

    def test_catalog_inspection(self):
        p = run("inspect_catalog.py", "--root", self.root)
        self.assertEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)["case_count"], 2)

    def test_jev_cannot_exclude_without_review(self):
        path = self.build([{
            "id": "org-transfer", "classification": "unrelated",
            "reason": "Jev choice only", "reviewed_by": None
        }])
        doc = json.loads(path.read_text())
        self.assertIn("org-transfer", [x["id"] for x in doc["selected_cases"]])

    def test_reviewed_unrelated_can_exclude(self):
        path = self.build([{
            "id": "org-transfer", "classification": "unrelated",
            "reason": "Only isolated authentication help text changed",
            "reviewed_by": "coding-agent"
        }])
        doc = json.loads(path.read_text())
        self.assertIn("org-transfer", [x["id"] for x in doc["excluded_cases"]])
        p = run("validate_selection.py", "--root", self.root, "--selection", path)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_mandatory_always_selected(self):
        path = self.build([{
            "id": "auth-login", "classification": "unrelated",
            "reason": "Reviewed", "reviewed_by": "coding-agent"
        }])
        doc = json.loads(path.read_text())
        self.assertIn("auth-login", [x["id"] for x in doc["selected_cases"]])

    def test_dry_run_never_uses_network(self):
        source = self.root / "input.json"
        source.write_text(json.dumps({
            "change_id": "PR-1",
            "change_summary": "Permission logic changed",
            "candidates": [{
                "id": "org-transfer",
                "behaviors": ["organization.transfer"],
                "components": ["PermissionService"],
                "api_routes": []
            }]
        }), encoding="utf-8")
        p = run("classify_with_jev.py", "--input", source, "--dry-run")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(json.loads(p.stdout)["network"])

    def test_jev_fixture_normalization(self):
        source = self.root / "input.json"
        source.write_text(json.dumps({
            "change_id": "PR-1",
            "change_summary": "Permission logic changed",
            "candidates": [{"id": "org-transfer",
                            "behaviors": [], "components": [],
                            "api_routes": []}]
        }), encoding="utf-8")
        fixture = self.root / "response.json"
        fixture.write_text(json.dumps({
            "model": "jev-1.14.0",
            "answers": {"q0": {"type": "choice", "choice": "indirect",
                                "confidence": 0.8,
                                "probabilities": {"indirect": 0.8}}}
        }), encoding="utf-8")
        p = run("classify_with_jev.py", "--input", source,
                "--fixture-response", fixture)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["assessments"][0]["classification"],
                         "indirect")


if __name__ == "__main__":
    unittest.main()
