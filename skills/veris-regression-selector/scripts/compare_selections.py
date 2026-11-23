#!/usr/bin/env python3
"""Compare two selection manifests without executing tests."""
import argparse
import json
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("previous")
    ap.add_argument("current")
    args = ap.parse_args()
    try:
        a = json.loads(Path(args.previous).read_text(encoding="utf-8"))
        b = json.loads(Path(args.current).read_text(encoding="utf-8"))
        if a.get("change_id") != b.get("change_id"):
            raise ValueError("Different change IDs")
        old = {x["id"] for x in a.get("selected_cases", [])}
        new = {x["id"] for x in b.get("selected_cases", [])}
        result = {
            "change_id": b["change_id"],
            "previous_run_id": a.get("run_id"),
            "current_run_id": b.get("run_id"),
            "newly_selected": sorted(new - old),
            "removed_from_selection": sorted(old - new),
            "unchanged_selected": sorted(old & new),
            "previous_breadth": a.get("breadth"),
            "current_breadth": b.get("breadth"),
            "previous_head": a.get("source", {}).get("head_revision"),
            "current_head": b.get("source", {}).get("head_revision"),
            "policy_changed": a.get("policy_sha256") != b.get("policy_sha256"),
            "catalog_changed": a.get("catalog_sha256") != b.get("catalog_sha256")
        }
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as e:
        print("Comparison error: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
