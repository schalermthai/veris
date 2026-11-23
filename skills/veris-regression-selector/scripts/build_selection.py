#!/usr/bin/env python3
"""Create conservative selection from catalog, policy, changes, assessments."""
import argparse
import json
import sys
from pathlib import Path
from _common import (catalog_cases, policy_load, load, digest, mandatory,
                     matched, breadth_max, LEVELS)


def select(root, changes_path, impact_path, run_id):
    catalog_path, cases = catalog_cases(root)
    policy_path, policy = policy_load(root)
    changes = load(changes_path)
    impact = load(impact_path)
    if impact.get("change_id") != changes.get("change_id"):
        raise ValueError("Impact and changes have different IDs")
    paths = changes.get("changed_files")
    if not isinstance(paths, list):
        raise ValueError("Missing changed_files")
    required, triggered = mandatory(policy, paths)
    missing = sorted(required - set(cases))
    breadth = "targeted"
    if changes.get("diff_truncated"):
        breadth = "full"
    max_files = policy.get("selection_limits", {}).get("max_changed_files_for_targeted", 40)
    if len(paths) > max_files:
        breadth = breadth_max(breadth, "broad")
    if any(matched(p, g) for p in paths
           for g in policy.get("cross_cutting_path_globs", [])):
        breadth = breadth_max(breadth, "broad")
    assessments = {}
    for item in impact.get("assessments", []):
        if item.get("id") in assessments:
            raise ValueError("Duplicate assessment for " + str(item.get("id")))
        assessments[item.get("id")] = item
    unknown_ids = []
    included = {}
    excluded = []
    for cid, case in cases.items():
        a = assessments.get(cid, {})
        label = a.get("classification", "unknown")
        if label not in {"direct", "indirect", "possible", "unrelated", "unknown"}:
            label = "unknown"
        reason = a.get("reason") if isinstance(a.get("reason"), str) else ""
        review = a.get("reviewed_by")
        if label == "unknown":
            unknown_ids.append(cid)
        if cid in required:
            included[cid] = {"id": cid, "impact": "mandatory",
                             "reason": "Required by policy", "sources": triggered}
        elif label == "unrelated" and review == "coding-agent" and reason.strip():
            excluded.append({"id": cid, "reason": reason, "reviewed_by": review})
        else:
            included[cid] = {"id": cid,
                             "impact": label if label != "unrelated" else "possible",
                             "reason": reason if reason and label != "unrelated"
                                       else "Not safely excluded; included conservatively",
                             "sources": []}
    # Missing semantic analysis means the test remains selected.
    if unknown_ids and len(unknown_ids) > len(cases) // 2:
        breadth = breadth_max(breadth, "broad")
    # Expand by breadth. In broad mode, protect critical/high cases.
    if breadth == "broad":
        for cid, case in cases.items():
            if case["risk"] in {"critical", "high"}:
                included.setdefault(cid, {
                    "id": cid, "impact": "risk-baseline",
                    "reason": "Broad selection includes high/critical tests",
                    "sources": []
                })
    if breadth == "full":
        for cid in cases:
            included.setdefault(cid, {
                "id": cid, "impact": "full",
                "reason": "Full regression selection",
                "sources": []
            })
    # Restore any case previously excluded if breadth now requires it.
    excluded = [x for x in excluded if x["id"] not in included]
    gaps = impact.get("coverage_gaps", [])
    if not isinstance(gaps, list):
        raise ValueError("coverage_gaps must be a list")
    high_gaps = any(isinstance(g, dict) and g.get("risk") in {"critical", "high"} for g in gaps)
    status = "blocked" if missing or not cases else (
        "needs_review" if high_gaps else "ready_for_runner"
    )
    return {
        "schema_version": 1,
        "change_id": changes.get("change_id"),
        "run_id": run_id,
        "source": {
            "changes_file": str(changes_path.relative_to(root)),
            "base_revision": changes.get("base_revision"),
            "head_revision": changes.get("head_revision"),
            "diff_sha256": changes.get("diff_sha256")
        },
        "catalog_sha256": digest(catalog_path),
        "policy_sha256": digest(policy_path),
        "status": status,
        "breadth": breadth,
        "mandatory_case_ids": sorted(required),
        "missing_mandatory_case_ids": missing,
        "triggered_rules": triggered,
        "selected_cases": sorted(included.values(), key=lambda x: x["id"]),
        "excluded_cases": sorted(excluded, key=lambda x: x["id"]),
        "coverage_gaps": gaps,
        "uncertainties": [
            "No assessment for case " + cid for cid in unknown_ids
        ],
        "classification_provider": impact.get("provider", "coding-agent")
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--changes", required=True)
    ap.add_argument("--impact", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", default="run-0001")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    try:
        changes = Path(args.changes).resolve()
        impact = Path(args.impact).resolve()
        if not changes.is_relative_to(root) or not impact.is_relative_to(root):
            raise ValueError("Input files must reside in project")
        result = select(root, changes, impact, args.run_id)
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as h:
            json.dump(result, h, indent=2)
            h.write("\n")
        print(json.dumps({
            "manifest": str(target),
            "status": result["status"],
            "breadth": result["breadth"],
            "selected": len(result["selected_cases"]),
            "excluded": len(result["excluded_cases"])
        }, indent=2))
        return 0 if result["status"] == "ready_for_runner" else 1
    except (OSError, ValueError, TypeError, KeyError) as e:
        print("Selection build error: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
