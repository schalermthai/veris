#!/usr/bin/env python3
"""Validate provenance, test metadata, and recorded execution evidence."""
import argparse
import json
import sys
from pathlib import Path
from _common import check_story, good_text, inside, read_json, relative_file, valid_id

KINDS = {"deterministic-e2e", "hybrid-e2e", "agentic-e2e"}
RISKS = {"critical", "high", "medium", "low"}


def validate(root, case_path):
    root = root.resolve()
    errors, warnings = [], []
    if not inside(case_path, root / ".veris" / "regression" / "cases"):
        raise ValueError("Case must reside in .veris/regression/cases")
    doc = read_json(case_path)
    case_id = doc.get("id")
    if doc.get("schema_version") != 1 or not valid_id(case_id):
        errors.append("Invalid schema version or case ID")
        return doc, errors, warnings
    if case_path.name != case_id + ".json":
        errors.append("Case filename must match case ID")
    if doc.get("status") not in {"draft", "ready"}:
        errors.append("Status must be draft or ready")
    if not good_text(doc.get("title")):
        errors.append("Missing case title")
    src = doc.get("source")
    if not isinstance(src, dict):
        errors.append("Missing source")
        return doc, errors, warnings
    try:
        source_path = relative_file(root, src.get("results_file"))
        source_doc, source_errors = check_story(root, source_path)
        errors += ["Source: " + x for x in source_errors]
        for field, source_field in [
            ("story_id", "story_id"),
            ("run_id", "run_id"),
            ("revision", "implementation_revision")
        ]:
            if src.get(field) != source_doc.get(source_field):
                errors.append("Source " + field + " mismatch")
        scenario_map = {
            s.get("id"): s for s in source_doc.get("scenarios", [])
            if isinstance(s, dict)
        }
        chosen = src.get("scenario_ids")
        covered = set()
        if not isinstance(chosen, list) or not chosen:
            errors.append("Must reference at least one source scenario")
        else:
            for sid in chosen:
                scenario = scenario_map.get(sid)
                if not scenario or scenario.get("status") != "pass":
                    errors.append("Unknown/unverified source scenario: " + str(sid))
                else:
                    covered.update(scenario.get("criterion_ids", []))
        refs = src.get("criterion_ids")
        if not isinstance(refs, list) or not refs or not set(refs).issubset(covered):
            errors.append("Invalid source criterion references")
    except (ValueError, OSError, TypeError) as e:
        errors.append("Source error: " + str(e))

    coverage = doc.get("coverage")
    test = doc.get("test")
    execution = doc.get("execution")
    if not isinstance(coverage, dict) or not isinstance(test, dict) or not isinstance(execution, dict):
        errors.append("Missing coverage, test, or execution object")
        return doc, errors, warnings

    if not valid_id(coverage.get("suite")):
        errors.append("Invalid suite")
    if coverage.get("risk") not in RISKS:
        errors.append("Invalid risk")
    for field in ("behaviors", "surfaces", "components", "api_routes", "tags"):
        value = coverage.get(field)
        if not isinstance(value, list) or any(not good_text(x) for x in value):
            errors.append("Invalid coverage array: " + field)
    if test.get("kind") not in KINDS:
        errors.append("Invalid test kind")
    if not isinstance(test.get("surface_actions"), list):
        errors.append("Missing surface_actions array")
    if not isinstance(test.get("assertions"), list):
        errors.append("Missing assertions array")

    if doc.get("status") == "ready":
        for field in ("file", "name", "framework", "command", "cleanup"):
            if not good_text(test.get(field)):
                errors.append("Ready case missing test." + field)
        if not coverage.get("behaviors") or not coverage.get("surfaces"):
            errors.append("Ready case missing behaviors or surfaces")
        if not test.get("surface_actions") or not test.get("assertions"):
            errors.append("Ready case needs real surface actions and assertions")
        try:
            relative_file(root, test.get("file"))
        except (OSError, ValueError, TypeError) as e:
            errors.append("Test file: " + str(e))

        runs = execution.get("runs")
        if not isinstance(runs, list):
            errors.append("Execution runs must be a list")
            runs = []
        seen = set()
        passing = 0
        evidence_root = root / ".veris" / "regression" / "evidence" / case_id
        for run in runs:
            if not isinstance(run, dict):
                errors.append("Invalid execution run record")
                continue
            rid = run.get("id")
            if not valid_id(rid) or rid in seen:
                errors.append("Invalid or duplicate execution ID")
                continue
            seen.add(rid)
            for item in run.get("evidence", []):
                try:
                    artifact = relative_file(root, item)
                    if not inside(artifact, evidence_root):
                        errors.append("Evidence outside case evidence directory")
                except (OSError, ValueError, TypeError) as e:
                    errors.append("Run evidence: " + str(e))
            if run.get("status") == "pass":
                if (run.get("clean_state") is not True
                    or run.get("exit_code") != 0
                    or not good_text(run.get("revision"))
                    or run.get("command") != test.get("command")
                    or not isinstance(run.get("evidence"), list)
                    or not run.get("evidence")):
                    errors.append("Incomplete passing run: " + rid)
                else:
                    passing += 1
        if passing < 2:
            errors.append("Ready case requires two documented clean-state passes")
    else:
        warnings.append("Draft case is not publishable regression coverage")
    warnings.append("Metadata and file existence do not prove test correctness")
    return doc, errors, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--case", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    path = (root / args.case).resolve()
    try:
        doc, errors, warnings = validate(root, path)
        result = {
            "case_id": doc.get("id"),
            "status": doc.get("status"),
            "valid": not errors,
            "publishable": not errors and doc.get("status") == "ready",
            "errors": errors,
            "warnings": warnings
        }
        print(json.dumps(result, indent=2))
        return 0 if not errors else 1
    except (OSError, ValueError, TypeError) as e:
        print("Validation error: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
