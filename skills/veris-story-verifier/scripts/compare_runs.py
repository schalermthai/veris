#!/usr/bin/env python3
"""Compare two story verification runs by stable scenario IDs.

Distinguishes actual failures from scenarios omitted in a focused retest.
Exit: 0 comparison completed without observed PASS->FAIL;
      1 observed PASS->FAIL; 2 invalid input.
"""
import argparse
import json
import sys
from pathlib import Path

VALID = {"pass", "fail", "blocked", "inconclusive", "not_run"}


def load(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("scenarios"), list):
        raise ValueError("Expected object with scenarios array")
    if not isinstance(doc.get("story_id"), str) or not isinstance(doc.get("run_id"), str):
        raise ValueError("Missing story_id or run_id")
    index = {}
    for s in doc["scenarios"]:
        if not isinstance(s, dict) or not isinstance(s.get("id"), str):
            raise ValueError("Invalid scenario")
        if s["id"] in index:
            raise ValueError("Duplicate scenario ID: " + s["id"])
        if s.get("status") not in VALID:
            raise ValueError("Invalid scenario status: " + s["id"])
        index[s["id"]] = s["status"]
    return doc, index


def compare(previous, current):
    fixed, regressed, still_failing = [], [], []
    new_failures, lost_confirmation = [], []
    previously_passing_not_retested = []
    newly_observed, current_not_run = [], []

    for sid, old in previous.items():
        now = current.get(sid)
        if now is None or now == "not_run":
            if old == "pass":
                previously_passing_not_retested.append(sid)
            continue
        if old == "pass" and now == "fail":
            regressed.append(sid)
        elif old == "pass" and now in {"blocked", "inconclusive"}:
            lost_confirmation.append(sid)
        elif old == "fail" and now == "pass":
            fixed.append(sid)
        elif old == "fail" and now == "fail":
            still_failing.append(sid)
        elif old != "fail" and now == "fail":
            new_failures.append(sid)

    for sid, status in current.items():
        if sid not in previous:
            newly_observed.append(sid)
            if status == "fail":
                new_failures.append(sid)
        if status == "not_run":
            current_not_run.append(sid)

    return {
        "fixed": sorted(fixed),
        "regressed": sorted(regressed),
        "still_failing": sorted(still_failing),
        "new_failures": sorted(set(new_failures)),
        "lost_confirmation": sorted(lost_confirmation),
        "previously_passing_not_retested": sorted(
            previously_passing_not_retested
        ),
        "new_scenarios": sorted(newly_observed),
        "current_not_run": sorted(current_not_run),
        "verification_regression": bool(regressed)
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("previous")
    parser.add_argument("current")
    args = parser.parse_args()
    try:
        prev_doc, prev = load(args.previous)
        curr_doc, curr = load(args.current)
        if prev_doc["story_id"] != curr_doc["story_id"]:
            raise ValueError("Runs belong to different stories")
        result = compare(prev, curr)
        result["story_id"] = curr_doc["story_id"]
        result["previous_run_id"] = prev_doc["run_id"]
        result["current_run_id"] = curr_doc["run_id"]
        result["previous_revision"] = prev_doc.get("implementation_revision")
        result["current_revision"] = curr_doc.get("implementation_revision")
        result["note"] = (
            "This comparison reports recorded status transitions. "
            "Not-run scenarios are unconfirmed, not proven regressions."
        )
        print(json.dumps(result, indent=2))
        return 1 if result["verification_regression"] else 0
    except (OSError, ValueError, TypeError) as exc:
        print("Comparison error: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
