#!/usr/bin/env python3
"""Deterministic integrity gate for story verification results.

Validates schema, coverage, claims of PASS, and evidence file existence.
Cannot prove that the evidence is genuine or semantically convincing.
"""
import argparse
import json
import re
import sys
from pathlib import Path

MODES = {"targeted", "retest", "final"}
STATUSES = {"pass", "fail", "blocked", "inconclusive", "not_run"}
VERDICTS = {"verified", "failed", "partial", "blocked"}
DEFECT_STATUSES = {"open", "fixed", "wontfix"}
IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def good_text(value):
    return isinstance(value, str) and bool(value.strip())


def validate(doc, run_dir, expected_revision=None):
    errors, warnings = [], []

    if doc.get("schema_version") != 1:
        errors.append("Unsupported schema_version")
    if doc.get("mode") not in MODES:
        errors.append("Invalid mode")
    if doc.get("overall_verdict") not in VERDICTS:
        errors.append("Invalid overall_verdict")
    for field in ("story_id", "run_id"):
        if not good_text(doc.get(field)) or not IDENT.fullmatch(doc[field]):
            errors.append("Invalid " + field)

    if run_dir.name != doc.get("run_id"):
        errors.append("Run ID does not match results parent directory")
    if expected_revision is not None:
        if doc.get("implementation_revision") != expected_revision:
            errors.append("Implementation revision does not match requested revision")

    criteria = doc.get("criteria")
    scenarios = doc.get("scenarios")
    defects = doc.get("defects", [])
    if not isinstance(criteria, list) or not isinstance(scenarios, list):
        return {
            "errors": errors + ["criteria and scenarios must be arrays"],
            "warnings": warnings, "computed_verdict": None
        }
    if not isinstance(defects, list):
        errors.append("defects must be an array")
        defects = []

    criteria_by_id, scenarios_by_id = {}, {}
    for item in criteria:
        if not isinstance(item, dict):
            errors.append("Criterion is not an object")
            continue
        cid = item.get("id")
        if not good_text(cid) or not IDENT.fullmatch(cid):
            errors.append("Criterion has an invalid ID")
            continue
        if cid in criteria_by_id:
            errors.append("Duplicate criterion: " + cid)
        if not good_text(item.get("description")):
            errors.append("Criterion missing description: " + cid)
        if not isinstance(item.get("required"), bool):
            errors.append("Criterion required must be boolean: " + cid)
        criteria_by_id[cid] = item

    required_criteria = {
        cid for cid, item in criteria_by_id.items()
        if item.get("required") is True
    }
    coverage = {cid: [] for cid in criteria_by_id}
    required_scenarios = []

    for scenario in scenarios:
        if not isinstance(scenario, dict):
            errors.append("Scenario is not an object")
            continue
        sid = scenario.get("id")
        if not good_text(sid) or not IDENT.fullmatch(sid):
            errors.append("Scenario has an invalid ID")
            continue
        if sid in scenarios_by_id:
            errors.append("Duplicate scenario: " + sid)
        scenarios_by_id[sid] = scenario
        if not isinstance(scenario.get("required"), bool):
            errors.append("Scenario required must be boolean: " + sid)
        if scenario.get("status") not in STATUSES:
            errors.append("Invalid scenario status: " + sid)
        refs = scenario.get("criterion_ids")
        if not isinstance(refs, list) or not refs:
            errors.append("Scenario has no criterion IDs: " + sid)
            refs = []
        if len(refs) != len(set(r for r in refs if isinstance(r, str))):
            errors.append("Duplicate criterion reference in scenario: " + sid)
        for cid in refs:
            if not isinstance(cid, str) or cid not in criteria_by_id:
                errors.append("Unknown criterion reference: " + str(cid))
            elif scenario.get("required") is True:
                coverage[cid].append(sid)
        if scenario.get("required") is True:
            required_scenarios.append(scenario)

        if scenario.get("status") == "pass":
            if not good_text(scenario.get("actual")):
                errors.append("PASS scenario missing actual observation: " + sid)
            independent = scenario.get("independent_check")
            if not isinstance(independent, dict) or independent.get("status") != "pass":
                errors.append("PASS scenario lacks passing independent check: " + sid)
            evidence = scenario.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                errors.append("PASS scenario has no evidence: " + sid)
            else:
                for rel in evidence:
                    if not good_text(rel):
                        errors.append("Invalid evidence path: " + sid)
                        continue
                    path = run_dir / rel
                    try:
                        if not path.resolve().is_relative_to(run_dir.resolve()):
                            errors.append("Evidence path escapes run: " + sid)
                        elif not path.is_file() or path.stat().st_size == 0:
                            errors.append("Evidence missing or empty: " + str(rel))
                    except OSError:
                        errors.append("Could not read evidence: " + str(rel))

    for cid in sorted(required_criteria):
        if not coverage.get(cid):
            errors.append("Required criterion not covered by required scenario: " + cid)

    open_blocking = False
    for defect in defects:
        if not isinstance(defect, dict):
            errors.append("Invalid defect object")
            continue
        state = defect.get("status")
        if state not in DEFECT_STATUSES:
            errors.append("Invalid defect status: " + str(defect.get("id")))
        if not isinstance(defect.get("blocking"), bool):
            errors.append("Defect blocking must be boolean")
        if state == "open" and defect.get("blocking") is True:
            open_blocking = True

    if doc.get("mode") == "final" and not required_criteria:
        errors.append("Final verification requires acceptance criteria")

    if not required_scenarios:
        computed = "blocked"
    elif any(s.get("status") == "fail" for s in required_scenarios):
        computed = "failed"
    elif open_blocking:
        computed = "failed"
    elif (required_criteria
          and all(s.get("status") == "pass" for s in required_scenarios)
          and all(coverage.get(cid) for cid in required_criteria)):
        computed = "verified"
    elif any(s.get("status") in {"pass", "inconclusive"} for s in required_scenarios):
        computed = "partial"
    else:
        computed = "blocked"

    # An open blocking defect is a failure, even if the required
    # scenario list is empty or could not execute.
    if open_blocking:
        computed = "failed"

    if computed != doc.get("overall_verdict"):
        errors.append(
            "Recorded verdict %r differs from computed verdict %r"
            % (doc.get("overall_verdict"), computed)
        )

    if computed == "verified" and not good_text(doc.get("implementation_revision")):
        errors.append("VERIFIED requires a recorded implementation revision")
    if computed == "verified" and not required_criteria:
        errors.append("VERIFIED requires at least one required criterion")
    if doc.get("bootstrap_status") not in {
        "ready", "partial", "blocked", "missing", "unknown"
    }:
        warnings.append("Unknown bootstrap status")

    # The filesystem validator cannot attest that a generated report
    # accurately represents what actually happened.
    warnings.append("Evidence existence does not prove evidence correctness")
    return {
        "errors": errors,
        "warnings": warnings,
        "computed_verdict": computed,
        "recorded_verdict": doc.get("overall_verdict"),
        "required_criteria": sorted(required_criteria),
        "required_scenarios": len(required_scenarios),
        "coverage": coverage
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results")
    parser.add_argument("--expected-revision", default=None)
    args = parser.parse_args()
    path = Path(args.results).resolve()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise ValueError("Results must be a JSON object")
        result = validate(doc, path.parent, args.expected_revision)
        result["valid"] = not result["errors"]
        print(json.dumps(result, indent=2))
        return 0 if result["valid"] else 1
    except (OSError, ValueError, TypeError) as exc:
        print("Invalid results input: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
