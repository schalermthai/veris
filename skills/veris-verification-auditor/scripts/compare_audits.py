#!/usr/bin/env python3
"""Compare audit findings and metrics without mismatching benchmark labels."""
import argparse
import json
import sys
from pathlib import Path


def get(path):
    run = Path(path).resolve()
    findings = json.loads((run / "findings.json").read_text(encoding="utf-8"))
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    return findings, metrics


def compare(old_findings, old_metrics, new_findings, new_metrics):
    before = {
        x.get("fingerprint") for x in old_findings.get("findings", [])
        if isinstance(x, dict) and x.get("status") == "open"
    }
    now = {
        x.get("fingerprint") for x in new_findings.get("findings", [])
        if isinstance(x, dict) and x.get("status") == "open"
    }
    old_cases = old_metrics.get("benchmark_fingerprints", {})
    new_cases = new_metrics.get("benchmark_fingerprints", {})
    comparable = bool(old_cases) and old_cases == new_cases
    diffs = {}
    if comparable:
        for key, current in new_metrics.get("metrics", {}).items():
            previous = old_metrics.get("metrics", {}).get(key)
            if not isinstance(previous, dict) or not isinstance(current, dict):
                continue
            if previous.get("denominator") != current.get("denominator"):
                comparable = False
                diffs = {}
                break
            p, c = previous.get("value"), current.get("value")
            if p is not None and c is not None:
                diffs[key] = {
                    "previous": p,
                    "current": c,
                    "difference": c - p
                }
    return {
        "resolved_finding_fingerprints": sorted(before - now),
        "new_finding_fingerprints": sorted(now - before),
        "persistent_finding_fingerprints": sorted(before & now),
        "benchmarks_comparable": comparable,
        "metric_differences": diffs if comparable else {},
        "note": (
            "Finding comparison is structural; metric comparison requires "
            "identical labeled case files. Other environment or model "
            "changes can still affect interpretation."
        )
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("previous")
    p.add_argument("current")
    args = p.parse_args()
    try:
        a, am = get(args.previous)
        b, bm = get(args.current)
        print(json.dumps(compare(a, am, b, bm), indent=2))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print("Audit comparison failed: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
