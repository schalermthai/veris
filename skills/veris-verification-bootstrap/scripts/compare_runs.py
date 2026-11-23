#!/usr/bin/env python3
"""Compare two Veris bootstrap run results, preserving baseline regressions."""
import argparse
import json
import sys
from pathlib import Path

VALID = {"pass", "fail", "blocked", "not_run"}


def load(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("checks"), list):
        raise ValueError("Expected results object containing checks")
    index = {}
    for item in doc["checks"]:
        if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
            or item.get("status") not in VALID
            or not isinstance(item.get("required"), bool)):
            raise ValueError("Invalid check")
        if item["id"] in index:
            raise ValueError("Duplicate check ID")
        index[item["id"]] = item
    return doc, index


def compare(old, new):
    fixed, regressed, unresolved, added, removed = [], [], [], [], []
    for cid, item in old.items():
        current = new.get(cid)
        if current is None:
            removed.append(cid)
            if item["required"] or item["status"] == "pass":
                regressed.append(cid)
        elif item["status"] == "pass" and current["status"] != "pass":
            regressed.append(cid)
        elif item["status"] != "pass" and current["status"] == "pass":
            fixed.append(cid)
        elif item["status"] != "pass" and current["status"] != "pass":
            unresolved.append(cid)
    for cid in new:
        if cid not in old:
            added.append(cid)
    return {
        "fixed": sorted(fixed),
        "regressed": sorted(regressed),
        "unresolved": sorted(unresolved),
        "added": sorted(added),
        "removed": sorted(removed),
        "required_not_passing": sorted(
            cid for cid, item in new.items()
            if item["required"] and item["status"] != "pass"),
        "baseline_regression_detected": bool(regressed)
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("previous")
    p.add_argument("current")
    a = p.parse_args()
    try:
        old_doc, old = load(a.previous)
        new_doc, new = load(a.current)
        out = compare(old, new)
        out["previous_run_id"] = old_doc.get("run_id")
        out["current_run_id"] = new_doc.get("run_id")
        print(json.dumps(out, indent=2))
        return 1 if out["baseline_regression_detected"] else 0
    except (OSError, ValueError, TypeError) as error:
        print("Comparison error: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
