#!/usr/bin/env python3
"""Read-only cross-Veris consistency analysis. Writes into audit run only."""
import argparse
import json
import sys
from pathlib import Path
from _common import (
    is_run, writable, read_json, safe, finding, replace_findings,
    write_json, files_for_audit
)

VALID_STORY = {"pass", "fail", "blocked", "inconclusive", "not_run"}
VALID_RUNNER = {
    "pass", "fail", "blocked", "infra_error",
    "inconclusive", "flaky", "not_run"
}


def analyze(root):
    root = root.resolve()
    found = []

    def emit(component, category, severity, summary, evidence,
             expected, observed, recommendation, confidence="confirmed"):
        found.append(finding(
            "consistency", component, category, severity, summary,
            evidence, expected, observed, recommendation,
            "Repeat the relevant verifier or artifact integrity check",
            confidence
        ))

    for rel in (".veris/verification-profile.yaml",
                ".veris/verification-playbook.md"):
        if not (root / rel).is_file():
            emit("bootstrap", "invalid_reference", "high",
                 "Missing bootstrap artifact: " + rel, [],
                 "Required bootstrap file exists", "Not present",
                 "Run veris-verification-bootstrap mode=harden")

    for category, rel, path in files_for_audit(root):
        if category not in {
            "story-verifier", "regression-author",
            "regression-selector", "regression-runner"
        }:
            continue
        try:
            doc = read_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            emit(category, "invalid_reference", "high",
                 "Unreadable structured artifact: " + rel, [rel],
                 "Valid machine-readable JSON", str(error)[:250],
                 "Repair source artifact using the owning Veris skill")
            continue

        if category == "story-verifier":
            if doc.get("overall_verdict") == "verified":
                required = {
                    x.get("id") for x in doc.get("criteria", [])
                    if isinstance(x, dict) and x.get("required") is True
                }
                if not required:
                    emit(category, "inconsistent_verdict", "high",
                         "VERIFIED story has no required criteria: " + rel,
                         [rel], "Required acceptance criteria",
                         "No required criteria registered",
                         "Revisit story verification contract")
                coverage = set()
                for s in doc.get("scenarios", []):
                    if not isinstance(s, dict):
                        continue
                    if s.get("required") is not True:
                        continue
                    if s.get("status") != "pass":
                        emit(category, "inconsistent_verdict", "high",
                             "VERIFIED includes nonpassing scenario: " + rel,
                             [rel], "All required scenarios pass",
                             str(s.get("status")),
                             "Retest required behavior and recalculate verdict")
                        continue
                    oracle = s.get("independent_check", {})
                    if not isinstance(oracle, dict) or oracle.get("status") != "pass":
                        emit(category, "missing_evidence", "high",
                             "PASS scenario without independent check: " + rel,
                             [rel], "Independent check PASS", "Missing",
                             "Strengthen Story Verifier checker")
                    evidence = s.get("evidence", [])
                    if not evidence or any(
                        not isinstance(e, str)
                        or not (path.parent / e).resolve().is_relative_to(path.parent.resolve())
                        or not (path.parent / e).is_file()
                        for e in evidence
                    ):
                        emit(category, "missing_evidence", "high",
                             "PASS scenario missing evidence: " + rel,
                             [rel], "Existing evidence for each PASS",
                             "Evidence absent or invalid",
                             "Rerun scenario and preserve actual artifacts")
                    coverage.update(s.get("criterion_ids", []))
                if required - coverage:
                    emit(category, "missing_coverage", "high",
                         "VERIFIED story has uncovered criteria: " + rel,
                         [rel], "All required criteria covered",
                         str(sorted(required - coverage)),
                         "Add and execute required scenarios")

        elif category == "regression-author":
            cid = doc.get("id")
            if doc.get("status") == "ready":
                test = doc.get("test", {})
                test_path = test.get("file") if isinstance(test, dict) else None
                if not isinstance(test_path, str):
                    missing = True
                else:
                    try:
                        missing = not safe(root, test_path).is_file()
                    except (OSError, ValueError):
                        missing = True
                if missing:
                    emit(category, "invalid_reference", "high",
                         "READY regression case missing executable: " + str(cid),
                         [rel], "Registered test exists", "Test absent",
                         "Run veris-regression-author mode=stabilize")
                source = doc.get("source", {})
                source_file = source.get("results_file") if isinstance(source, dict) else None
                try:
                    original = read_json(safe(root, source_file))
                    if original.get("overall_verdict") != "verified":
                        raise ValueError("Source not VERIFIED")
                except (OSError, ValueError, TypeError):
                    emit(category, "invalid_reference", "high",
                         "READY regression case has invalid story source: " + str(cid),
                         [rel], "Verified final source",
                         "Missing, invalid, or unverified source",
                         "Restore provenance or reauthor the case")

        elif category == "regression-selector":
            selected = doc.get("selected_cases", [])
            excluded = doc.get("excluded_cases", [])
            if not isinstance(selected, list) or not isinstance(excluded, list):
                emit(category, "invalid_reference", "high",
                     "Invalid selection lists: " + rel, [rel],
                     "Selected and excluded lists", "Malformed data",
                     "Recreate selection")
                continue
            ids = [x.get("id") for x in selected if isinstance(x, dict)]
            others = [x.get("id") for x in excluded if isinstance(x, dict)]
            if len(ids) != len(set(ids)) or set(ids) & set(others):
                emit(category, "inconsistent_verdict", "high",
                     "Duplicate/overlapping selected and excluded cases: " + rel,
                     [rel], "Each case exactly once", "Overlap or duplication",
                     "Run veris-regression-selector mode=reselect")
            for item in excluded:
                if (not isinstance(item, dict)
                    or item.get("reviewed_by") != "coding-agent"
                    or not item.get("reason")):
                    emit(category, "missing_evidence", "medium",
                         "Unreviewed exclusion: " + rel, [rel],
                         "Reviewed exclusion rationale", "Review incomplete",
                         "Reevaluate excluded case independently")
                    break
            required = set(doc.get("mandatory_case_ids", []))
            if required - set(ids):
                emit(category, "missing_coverage", "high",
                     "Mandatory cases omitted: " + rel, [rel],
                     "All mandatory tests selected",
                     str(sorted(required - set(ids))),
                     "Rerun selector with policy enforcement")

        elif category == "regression-runner":
            cases = doc.get("cases", [])
            if not isinstance(cases, list):
                emit(category, "invalid_reference", "high",
                     "Malformed runner case records: " + rel, [rel],
                     "Case records array", "Absent",
                     "Rerun or repair execution report")
                continue
            statuses = [x.get("status") for x in cases if isinstance(x, dict)]
            expected = (
                "blocked" if not statuses else
                "failed" if "fail" in statuses else
                "blocked" if any(x in {"blocked", "infra_error", "not_run"} for x in statuses) else
                "inconclusive" if any(x in {"inconclusive", "flaky"} for x in statuses) else
                "passed" if all(x == "pass" for x in statuses) else "inconclusive"
            )
            if doc.get("overall_verdict") != expected:
                emit(category, "inconsistent_verdict", "high",
                     "Runner verdict conflicts with cases: " + rel,
                     [rel], expected, str(doc.get("overall_verdict")),
                     "Correct runner result parsing and verdict gate")
            for c in cases:
                if not isinstance(c, dict):
                    continue
                if c.get("status") == "pass" and (
                    c.get("cleanup") != "pass"
                    or not c.get("attempts")
                    or not any(
                        isinstance(a, dict) and a.get("status") == "pass"
                        and a.get("exit_code") == 0
                        for a in c.get("attempts", [])
                    )
                ):
                    emit(category, "missing_evidence", "high",
                         "Runner PASS lacks successful execution/cleanup: " + rel,
                         [rel], "Real passing attempt and cleanup",
                         "Absent or contradictory attempt",
                         "Fix runner evidence and outcome gate")
                if c.get("status") == "fail" and not (
                    isinstance(c.get("triage"), dict)
                    and c["triage"].get("confirmed") is True
                ):
                    emit(category, "missing_evidence", "high",
                         "Confirmed FAIL lacks triage: " + rel,
                         [rel], "Evidence-backed product triage",
                         "No confirmed triage record",
                         "Investigate failure classification")

    return sorted(found, key=lambda x: x["fingerprint"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--run", required=True)
    args = p.parse_args()
    root = Path(args.root).resolve()
    try:
        run = is_run(root, args.run)
        writable(run)
        found = analyze(root)
        write_json(run / "consistency.json", {
            "schema_version": 1,
            "run_id": run.name,
            "finding_count": len(found),
            "findings": found,
            "limitations": [
                "Artifact checks do not establish semantic test quality"
            ]
        })
        replace_findings(run, "consistency", found)
        print(json.dumps({
            "run_id": run.name,
            "findings": len(found),
            "consistency": str(run / "consistency.json")
        }, indent=2))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print("Consistency audit failed: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
