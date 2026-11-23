#!/usr/bin/env python3
"""Independent deterministic selection integrity gate."""
import argparse
import json
import sys
from pathlib import Path
from _common import (catalog_cases, policy_load, load, digest,
                     project_path, mandatory, matched, LEVELS)


def validate(root, filename):
    errors = []
    data = load(filename)
    catalog_path, catalog = catalog_cases(root)
    policy_path, policy = policy_load(root)
    source = data.get("source", {})
    path = project_path(root, source.get("changes_file", ""))
    changes = load(path)
    if data.get("schema_version") != 1:
        errors.append("Unsupported manifest schema")
    if data.get("change_id") != changes.get("change_id"):
        errors.append("Change ID mismatch")
    for key in ("base_revision", "head_revision", "diff_sha256"):
        if source.get(key) != changes.get(key):
            errors.append("Change source mismatch: " + key)
    if data.get("catalog_sha256") != digest(catalog_path):
        errors.append("Stale catalog identity")
    if data.get("policy_sha256") != digest(policy_path):
        errors.append("Stale policy identity")
    breadth = data.get("breadth")
    if breadth not in LEVELS:
        errors.append("Invalid breadth")
    selected = data.get("selected_cases", [])
    excluded = data.get("excluded_cases", [])
    if not isinstance(selected, list) or not isinstance(excluded, list):
        errors.append("Selected/excluded entries must be arrays")
        selected, excluded = [], []
    selected_ids = [x.get("id") for x in selected if isinstance(x, dict)]
    excluded_ids = [x.get("id") for x in excluded if isinstance(x, dict)]
    if len(selected_ids) != len(set(selected_ids)):
        errors.append("Duplicate selected ID")
    if len(excluded_ids) != len(set(excluded_ids)):
        errors.append("Duplicate excluded ID")
    sel, exc = set(selected_ids), set(excluded_ids)
    if sel & exc:
        errors.append("Selected/excluded overlap")
    if (sel | exc) != set(catalog):
        errors.append("Not every catalog case accounted for")
    required, triggered = mandatory(policy, changes.get("changed_files", []))
    if not required.issubset(sel):
        errors.append("Mandatory tests not selected")
    if set(data.get("mandatory_case_ids", [])) != required:
        errors.append("Mandatory case ID mismatch")
    if set(data.get("triggered_rules", [])) != set(triggered):
        errors.append("Triggered policy rule mismatch")
    missing = required - set(catalog)
    if set(data.get("missing_mandatory_case_ids", [])) != missing:
        errors.append("Missing mandatory ID record differs from policy")
    if changes.get("diff_truncated") and breadth != "full":
        errors.append("Truncated diff requires full selection")
    if breadth == "full" and sel != set(catalog):
        errors.append("Full selection must include every case")
    if breadth == "broad" and not {
        cid for cid, case in catalog.items()
        if case["risk"] in {"critical", "high"}
    }.issubset(sel):
        errors.append("Broad selection lacks high/critical cases")
    if any(matched(p, g) for p in changes.get("changed_files", [])
           for g in policy.get("cross_cutting_path_globs", [])):
        if breadth not in {"broad", "full"}:
            errors.append("Cross-cutting diff requires broad/full")
    maximum = policy.get("selection_limits", {}).get("max_changed_files_for_targeted", 40)
    if len(changes.get("changed_files", [])) > maximum:
        if breadth not in {"broad", "full"}:
            errors.append("Large diff requires broad/full")
    for item in excluded:
        if (not isinstance(item, dict) or item.get("reviewed_by") != "coding-agent"
            or not isinstance(item.get("reason"), str)
            or not item["reason"].strip()):
            errors.append("Unreviewed exclusion")
    for item in selected:
        if not isinstance(item, dict) or not isinstance(item.get("reason"), str) or not item["reason"].strip():
            errors.append("Selected case missing reason")
    if missing and data.get("status") != "blocked":
        errors.append("Missing mandatory case requires blocked status")
    gaps = data.get("coverage_gaps", [])
    if any(isinstance(g, dict) and g.get("risk") in {"high", "critical"} for g in gaps):
        if data.get("status") == "ready_for_runner":
            errors.append("High-risk gap requires review")
    if data.get("status") not in {"blocked", "needs_review", "ready_for_runner"}:
        errors.append("Invalid status")
    if not catalog and data.get("status") != "blocked":
        errors.append("Empty catalog cannot be runner-ready")
    return {
        "valid": not errors,
        "errors": errors,
        "selected_count": len(sel),
        "excluded_count": len(exc),
        "mandatory_count": len(required),
        "status": data.get("status")
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--selection", required=True)
    args = ap.parse_args()
    try:
        result = validate(Path(args.root).resolve(),
                          Path(args.selection).resolve())
        print(json.dumps(result, indent=2))
        return 0 if result["valid"] else 1
    except (OSError, ValueError, TypeError, KeyError) as e:
        print("Validation error: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
