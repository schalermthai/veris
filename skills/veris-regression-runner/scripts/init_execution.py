#!/usr/bin/env python3
"""Allocate an immutable Veris regression execution run."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from _core import check_inputs, computed_verdict, summary


def initialize(root, selection):
    context = check_inputs(root, selection, verify_git=True)
    doc = context["selection"]
    output_root = root / ".veris" / "regression" / "executions" / doc["change_id"]
    runs = output_root / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    folder = None
    for num in range(1, 100001):
        candidate = runs / ("run-%04d" % num)
        try:
            candidate.mkdir(exist_ok=False)
            folder = candidate
            break
        except FileExistsError:
            continue
    if folder is None:
        raise RuntimeError("No available execution run ID")
    (folder / "evidence").mkdir()
    (folder / "evidence" / ".gitignore").write_text(
        "*\n!.gitignore\n", encoding="utf-8"
    )
    selection_rel = str(context["selection_file"].relative_to(root))
    cases = context["cases"]
    plan = {
        "schema_version": 1,
        "change_id": doc["change_id"],
        "run_id": folder.name,
        "selection_file": selection_rel,
        "selection_sha256": context["selection_hash"],
        "head_revision": doc["source"]["head_revision"],
        "catalog_sha256": doc["catalog_sha256"],
        "policy_sha256": doc["policy_sha256"],
        "execution_policy_sha256": context["execution_policy_hash"],
        "strategy": "serial-per-case",
        "cases": cases
    }
    results = {
        "schema_version": 1,
        "change_id": doc["change_id"],
        "run_id": folder.name,
        "selection_file": selection_rel,
        "selection_sha256": context["selection_hash"],
        "application_revision": doc["source"]["head_revision"],
        "mode": "run",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "overall_verdict": "blocked",
        "cases": [
            {"id": c["id"], "status": "not_run", "attempts": [],
             "cleanup": "not_run", "triage": None, "notes": ""}
            for c in cases
        ]
    }
    results["summary"] = summary(results["cases"])
    (folder / "execution-plan.json").write_text(
        json.dumps(plan, indent=2) + "\n", encoding="utf-8"
    )
    (folder / "results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    (folder / "execution-report.md").write_text(
        "# Veris Regression Execution\n\n"
        + "Run: " + folder.name + "\n\n"
        + "Status: NOT_RUN\n\n"
        + "See results.json; do not claim completion until execution.\n",
        encoding="utf-8"
    )
    return {
        "run_id": folder.name,
        "run_directory": str(folder),
        "plan": str(folder / "execution-plan.json"),
        "results": str(folder / "results.json")
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--selection", required=True)
    a = ap.parse_args()
    root = Path(a.root).resolve()
    try:
        result = initialize(root, Path(a.selection).resolve())
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print("Execution initialization failed: " + str(error),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
