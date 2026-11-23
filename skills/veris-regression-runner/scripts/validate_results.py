#!/usr/bin/env python3
"""Deterministic integrity gate for Veris regression execution results."""
import argparse
import json
import sys
from pathlib import Path
from _core import (load, digest, inside, CASE_STATES,
                   computed_verdict, summary)


def verify(root, results_path):
    root = Path(root).resolve()
    results_path = Path(results_path).resolve()
    if not inside(results_path, root / ".veris/regression/executions"):
        raise ValueError("Results not in regression execution directory")
    data = load(results_path)
    folder = results_path.parent
    plan = load(folder / "execution-plan.json")
    sel_file = root / plan.get("selection_file", "")
    selection = load(sel_file)
    errors = []

    if data.get("schema_version") != 1 or plan.get("schema_version") != 1:
        errors.append("Unsupported schema version")
    for field in ("change_id", "run_id"):
        if data.get(field) != plan.get(field):
            errors.append(field + " differs from execution plan")
    if data.get("run_id") != folder.name:
        errors.append("Run ID differs from parent folder")
    if data.get("selection_sha256") != digest(sel_file):
        errors.append("Selection digest changed")
    if plan.get("selection_sha256") != digest(sel_file):
        errors.append("Plan selection digest changed")
    if data.get("application_revision") != plan.get("head_revision"):
        errors.append("Execution revision differs from plan")
    if data.get("application_revision") != selection.get("source", {}).get(
        "head_revision"
    ):
        errors.append("Execution revision differs from selection")
    recorded = data.get("cases")
    selected = plan.get("cases")
    if not isinstance(recorded, list) or not isinstance(selected, list):
        raise ValueError("Invalid cases arrays")
    ids = [x.get("id") for x in recorded if isinstance(x, dict)]
    target = [x.get("id") for x in selected if isinstance(x, dict)]
    if len(ids) != len(recorded) or len(ids) != len(set(ids)):
        errors.append("Duplicate or malformed result case IDs")
    if set(ids) != set(target) or len(ids) != len(target):
        errors.append("Results do not cover the planned selection")

    for case in recorded:
        if not isinstance(case, dict):
            continue
        cid = case.get("id")
        status = case.get("status")
        if status not in CASE_STATES:
            errors.append("Invalid case status: " + str(cid))
        attempts = case.get("attempts")
        if not isinstance(attempts, list):
            errors.append("Attempts must be an array: " + str(cid))
            continue
        seen = set()
        for attempt in attempts:
            idx = attempt.get("attempt")
            if idx in seen:
                errors.append("Duplicate attempt: " + str(cid))
            seen.add(idx)
            for rel in attempt.get("evidence", []):
                if not isinstance(rel, str) or not rel:
                    errors.append("Invalid evidence reference: " + str(cid))
                    continue
                path = (folder / rel).resolve()
                if not inside(path, folder) or not path.is_file():
                    errors.append("Evidence missing or outside run: " + rel)
        if status == "pass":
            if case.get("cleanup") != "pass":
                errors.append("PASS without successful cleanup: " + str(cid))
            if not attempts or not any(
                a.get("status") == "pass" and a.get("exit_code") == 0
                and a.get("evidence") for a in attempts
            ):
                errors.append("PASS without execution proof: " + str(cid))
        if status == "fail":
            triage = case.get("triage")
            if (not isinstance(triage, dict)
                or triage.get("confirmed") is not True
                or triage.get("category") != "product_regression"
                or not triage.get("reviewed_by")
                or not triage.get("reason")
                or not triage.get("evidence")):
                errors.append("FAIL missing evidence-backed triage: " + str(cid))
            else:
                for rel in triage["evidence"]:
                    path = (folder / rel).resolve()
                    if not inside(path, folder) or not path.is_file():
                        errors.append("Triage evidence missing: " + str(cid))
        if status == "not_run" and attempts:
            errors.append("NOT_RUN cannot have attempts: " + str(cid))

    expected = computed_verdict(recorded)
    if data.get("overall_verdict") != expected:
        errors.append("Overall verdict inconsistent with case outcomes")
    if data.get("summary") != summary(recorded):
        errors.append("Summary counts do not match results")
    if data.get("mode") == "retest" and expected == "passed":
        # A retest that actually covered the full selection may pass.
        # A partial retest has not_run cases, preventing PASSED above.
        pass
    return {
        "valid": not errors,
        "errors": errors,
        "computed_verdict": expected,
        "case_count": len(recorded),
        "summary": summary(recorded),
        "warning": "Evidence existence cannot independently prove test correctness"
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--results", required=True)
    a = ap.parse_args()
    try:
        result = verify(Path(a.root).resolve(),
                        Path(a.results).resolve())
        print(json.dumps(result, indent=2))
        return 0 if result["valid"] else 1
    except (OSError, ValueError, TypeError, KeyError) as error:
        print("Result validation error: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
