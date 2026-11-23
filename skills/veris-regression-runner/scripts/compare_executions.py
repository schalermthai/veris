#!/usr/bin/env python3
"""Compare immutable regression run results without implying unrun tests passed."""
import argparse
import json
import sys
from pathlib import Path


def compare(old, new):
    prior = {x["id"]: x["status"] for x in old["cases"]}
    current = {x["id"]: x["status"] for x in new["cases"]}
    fixed, regressed, still_failing, lost, not_rerun = [], [], [], [], []
    new_failures = []
    bad = {"fail", "inconclusive", "flaky", "infra_error", "blocked"}
    for cid, before in prior.items():
        after = current.get(cid, "not_run")
        if after == "not_run":
            if before == "pass":
                not_rerun.append(cid)
        elif before in bad and after == "pass":
            fixed.append(cid)
        elif before == "pass" and after == "fail":
            regressed.append(cid)
        elif before == "pass" and after in bad:
            lost.append(cid)
        elif before in bad and after in bad:
            still_failing.append(cid)
    for cid, after in current.items():
        if cid not in prior and after in bad:
            new_failures.append(cid)
    return {
        "change_id": new["change_id"],
        "previous_run_id": old["run_id"],
        "current_run_id": new["run_id"],
        "fixed": sorted(fixed),
        "regressed": sorted(regressed),
        "still_failing": sorted(still_failing),
        "lost_confirmation": sorted(lost),
        "previously_passing_not_retested": sorted(not_rerun),
        "new_failures": sorted(new_failures),
        "revision_changed": (
            old.get("application_revision") != new.get("application_revision")
        ),
        "previous_verdict": old.get("overall_verdict"),
        "current_verdict": new.get("overall_verdict")
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("previous")
    ap.add_argument("current")
    a = ap.parse_args()
    try:
        old = json.loads(Path(a.previous).read_text(encoding="utf-8"))
        new = json.loads(Path(a.current).read_text(encoding="utf-8"))
        if old.get("change_id") != new.get("change_id"):
            raise ValueError("Runs belong to different changes")
        result = compare(old, new)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("Comparison failed: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
