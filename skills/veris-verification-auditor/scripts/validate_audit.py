#!/usr/bin/env python3
"""Validate a Veris audit and optionally seal immutable history."""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from _common import (
    is_run, writable, read_json, safe, file_sha,
    COMPONENTS, SEVERITIES, CONFIDENCES, write_json
)

VERDICTS = {"HEALTHY", "NEEDS_HARDENING", "INCONCLUSIVE", "BLOCKED"}


def validate(root, run):
    errors = []
    plan = read_json(run / "audit-plan.json")
    index = read_json(run / "evidence-index.json")
    results = read_json(run / "findings.json")
    metrics = read_json(run / "metrics.json")
    report = (run / "audit-report.md").read_text(encoding="utf-8")
    mode = plan.get("mode")

    if plan.get("run_id") != run.name:
        errors.append("Plan run ID mismatch")
    if index.get("run_id") != run.name:
        errors.append("Index run ID mismatch")
    if results.get("run_id") != run.name:
        errors.append("Findings run ID mismatch")
    if metrics.get("run_id") != run.name:
        errors.append("Metrics run ID mismatch")
    if mode not in {"audit", "benchmark", "incident", "challenge"}:
        errors.append("Invalid mode")

    sources = index.get("sources", [])
    if not isinstance(sources, list) or not sources:
        errors.append("No source evidence indexed")
        sources = []
    if plan.get("source_count") != len(sources):
        errors.append("Source count differs from index")
    for item in sources:
        try:
            path = safe(root, item["path"])
            if file_sha(path) != item["sha256"]:
                errors.append("Indexed source changed: " + item["path"])
        except (OSError, ValueError, KeyError, TypeError):
            errors.append("Indexed source missing or invalid")

    if not (run / "consistency.json").is_file():
        errors.append("Consistency check has not been performed")

    if mode == "benchmark" and not (run / "benchmark-results.json").is_file():
        errors.append("Benchmark results missing")
    if mode == "incident" and "Incident" not in report:
        errors.append("Incident report must document investigation")
    if mode == "challenge":
        approval = plan.get("approval", {})
        if (approval.get("challenge_authorized") is not True
            or approval.get("disposable_environment_confirmed") is not True):
            errors.append("Challenge approval/isolation not established")
        if not (run / "challenge-results.json").is_file():
            errors.append("Challenge evidence/results missing")

    findings = results.get("findings", [])
    if not isinstance(findings, list):
        errors.append("Malformed findings array")
        findings = []
    seen = set()
    for item in findings:
        if not isinstance(item, dict):
            errors.append("Finding is not an object")
            continue
        fid = item.get("id")
        if fid in seen or not isinstance(fid, str):
            errors.append("Duplicate or missing finding ID")
        seen.add(fid)
        if item.get("component") not in COMPONENTS:
            errors.append("Invalid finding component")
        if item.get("severity") not in SEVERITIES:
            errors.append("Invalid finding severity")
        if item.get("confidence") not in CONFIDENCES:
            errors.append("Invalid finding confidence")
        for field in ("summary", "expected", "observed",
                      "recommendation", "validation"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append("Finding missing " + field)
        evidence = item.get("evidence")
        if not isinstance(evidence, list):
            errors.append("Finding evidence must be an array")
            continue
        if item.get("confidence") == "confirmed" and not evidence:
            errors.append("Confirmed finding has no evidence: " + str(fid))
        for rel in evidence:
            try:
                safe(root, rel)
            except (OSError, ValueError, TypeError):
                errors.append("Finding evidence missing: " + str(fid))

    for name, measurement in metrics.get("metrics", {}).items():
        if not isinstance(measurement, dict):
            errors.append("Invalid metric: " + name)
            continue
        num = measurement.get("numerator")
        den = measurement.get("denominator")
        value = measurement.get("value")
        if (not isinstance(num, int) or isinstance(num, bool)
            or not isinstance(den, int) or isinstance(den, bool)
            or not 0 <= num <= den):
            errors.append("Invalid metric numerator/denominator: " + name)
            continue
        if den == 0:
            if value is not None:
                errors.append("Zero-denominator metric must be null: " + name)
        elif (not isinstance(value, (float, int))
              or abs(value - num / den) > 0.00000001):
            errors.append("Invalid metric value: " + name)

    chosen = None
    for value in VERDICTS:
        if "Overall verdict: " + value in report:
            if chosen is not None:
                errors.append("Multiple overall verdicts")
            chosen = value
    if chosen is None:
        errors.append("Report missing finalized overall verdict")
    if "pending review" in report.lower():
        errors.append("Report still contains draft placeholders")

    confirmed_blockers = [
        item for item in findings
        if isinstance(item, dict)
        and item.get("status") == "open"
        and item.get("confidence") == "confirmed"
        and item.get("severity") in {"critical", "high"}
    ]
    if chosen == "HEALTHY" and confirmed_blockers:
        errors.append("HEALTHY incompatible with confirmed high/critical findings")
    if chosen == "HEALTHY" and index.get("collection_errors"):
        errors.append("HEALTHY incompatible with incomplete source inventory")
    if chosen == "HEALTHY" and not sources:
        errors.append("HEALTHY requires actual audited sources")

    return {
        "valid": not errors,
        "errors": errors,
        "run_id": run.name,
        "verdict": chosen,
        "findings": len(findings),
        "indexed_sources": len(sources),
        "warning": "Artifact validity does not prove independent semantic correctness"
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--run", required=True)
    p.add_argument("--seal", action="store_true")
    args = p.parse_args()
    root = Path(args.root).resolve()
    try:
        run = is_run(root, args.run)
        if args.seal:
            writable(run)
        outcome = validate(root, run)
        if outcome["valid"] and args.seal:
            assets = [
                "audit-plan.json", "evidence-index.json", "findings.json",
                "metrics.json", "audit-report.md", "consistency.json"
            ]
            if (run / "benchmark-results.json").exists():
                assets.append("benchmark-results.json")
            seal = {
                "schema_version": 1,
                "run_id": run.name,
                "sealed_at": datetime.now(timezone.utc).isoformat(),
                "verdict": outcome["verdict"],
                "artifact_hashes": {
                    name: file_sha(run / name) for name in assets
                }
            }
            write_json(run / "audit-seal.json", seal)
            latest = root / ".veris/audits/latest-report.md"
            latest.write_text(
                (run / "audit-report.md").read_text(encoding="utf-8"),
                encoding="utf-8"
            )
        print(json.dumps(outcome, indent=2))
        return 0 if outcome["valid"] else 1
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("Audit validation failed: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
