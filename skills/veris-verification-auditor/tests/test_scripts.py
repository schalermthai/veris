"""Offline tests for Veris Auditor scripts. No Docker or API required."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def call(script, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        capture_output=True, text=True, timeout=20
    )


class AuditorScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        veris = self.root / ".veris"
        veris.mkdir()
        (veris / "verification-profile.yaml").write_text(
            "schema_version: 1\nbootstrap:\n  status: ready\n",
            encoding="utf-8"
        )
        (veris / "verification-playbook.md").write_text(
            "# Test playbook\n", encoding="utf-8"
        )
        story = veris / "stories" / "STORY-142" / "runs" / "run-0001"
        (story / "evidence").mkdir(parents=True)
        (story / "evidence" / "proof.txt").write_text(
            "observed", encoding="utf-8"
        )
        (story / "results.json").write_text(json.dumps({
            "schema_version": 1,
            "story_id": "STORY-142",
            "run_id": "run-0001",
            "mode": "final",
            "overall_verdict": "verified",
            "criteria": [{
                "id": "AC-1", "description": "Transfer", "required": True
            }],
            "scenarios": [{
                "id": "S-01",
                "criterion_ids": ["AC-1"],
                "required": True,
                "status": "pass",
                "actual": "Transfer observed",
                "independent_check": {"status": "pass"},
                "evidence": ["evidence/proof.txt"]
            }]
        }, indent=2), encoding="utf-8")

    def new_run(self, mode="audit"):
        p = call("collect_evidence.py", "--root", self.root, "--mode", mode)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return Path(json.loads(p.stdout)["run_directory"])

    def test_collect_preserves_history(self):
        first = self.new_run()
        second = self.new_run()
        self.assertNotEqual(first, second)
        self.assertTrue((first / "evidence-index.json").exists())
        self.assertTrue((second / "evidence-index.json").exists())

    def test_consistency_clean_story(self):
        folder = self.new_run()
        p = call("check_consistency.py", "--root", self.root, "--run", folder)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        findings = json.loads((folder / "findings.json").read_text())
        self.assertEqual(findings["findings"], [])

    def test_consistency_catches_false_verified(self):
        story = (self.root / ".veris/stories/STORY-142/runs/run-0001/results.json")
        doc = json.loads(story.read_text())
        doc["scenarios"][0]["status"] = "fail"
        story.write_text(json.dumps(doc), encoding="utf-8")
        folder = self.new_run()
        p = call("check_consistency.py", "--root", self.root, "--run", folder)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        entries = json.loads((folder / "findings.json").read_text())["findings"]
        self.assertTrue(any(
            x["category"] == "inconsistent_verdict" for x in entries
        ))

    def test_benchmark_recall(self):
        bench = self.root / ".veris/audits/benchmarks"
        bench.mkdir(parents=True)
        (bench / "truth.md").write_text(
            "Independent review established relevance", encoding="utf-8"
        )
        selection = self.root / ".veris/regression/selections/PR-1/runs/run-0001"
        selection.mkdir(parents=True)
        (selection / "selection.json").write_text(json.dumps({
            "selected_cases": [{"id": "auth-login"}]
        }), encoding="utf-8")
        (bench / "BENCH-001.json").write_text(json.dumps({
            "schema_version": 1,
            "id": "BENCH-001",
            "kind": "selection",
            "ground_truth": {
                "status": "confirmed",
                "reviewer": "independent reviewer",
                "evidence": [".veris/audits/benchmarks/truth.md"],
                "complete_labels": False
            },
            "observed_file": ".veris/regression/selections/PR-1/runs/run-0001/selection.json",
            "expected": {
                "relevant_case_ids": ["org-transfer"],
                "eligible_case_ids": []
            }
        }), encoding="utf-8")
        folder = self.new_run("benchmark")
        p = call("evaluate_benchmark.py", "--root", self.root, "--run", folder)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        metrics = json.loads((folder / "metrics.json").read_text())["metrics"]
        self.assertEqual(metrics["selection_recall"]["numerator"], 0)
        self.assertEqual(metrics["selection_recall"]["denominator"], 1)
        self.assertIsNone(metrics["selection_precision"]["value"])

    def test_validate_rejects_unfinished_report(self):
        folder = self.new_run()
        call("check_consistency.py", "--root", self.root, "--run", folder)
        p = call("validate_audit.py", "--root", self.root, "--run", folder)
        self.assertEqual(p.returncode, 1)
        self.assertIn("finalized overall verdict", p.stdout)

    def test_audit_seal_and_comparison(self):
        first = self.new_run()
        call("check_consistency.py", "--root", self.root, "--run", first)
        (first / "audit-report.md").write_text(
            "# Audit\n\nOverall verdict: INCONCLUSIVE\n\n"
            "Scope: story verification artifacts only\n\n"
            "Evidence reviewed; no labeled benchmark ground truth.\n",
            encoding="utf-8"
        )
        p = call("validate_audit.py", "--root", self.root,
                 "--run", first, "--seal")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue((first / "audit-seal.json").is_file())
        second = self.new_run()
        call("check_consistency.py", "--root", self.root, "--run", second)
        cmp = call("compare_audits.py", first, second)
        self.assertEqual(cmp.returncode, 0, cmp.stdout + cmp.stderr)
        self.assertFalse(json.loads(cmp.stdout)["benchmarks_comparable"])


if __name__ == "__main__":
    unittest.main()
