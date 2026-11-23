#!/usr/bin/env python3
"""Initialize immutable audit run; index source paths/hashes, not raw logs."""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from _common import files_for_audit, file_sha, write_json


def initialize(root, mode, limit):
    root = Path(root).resolve()
    if not root.is_dir() or not (root / ".veris").is_dir():
        raise ValueError("Expected project root with .veris directory")

    auditor = root / ".veris" / "audits"
    runs = auditor / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    policy = auditor / "policy.json"
    if not policy.exists():
        asset = Path(__file__).resolve().parent.parent / "assets" / "audit-policy.json"
        with policy.open("xb") as fh:
            fh.write(asset.read_bytes())

    folder = None
    for i in range(1, 100001):
        candidate = runs / ("run-%04d" % i)
        try:
            candidate.mkdir(exist_ok=False)
            folder = candidate
            break
        except FileExistsError:
            continue
    if folder is None:
        raise RuntimeError("No available run ID")

    evidence_dir = folder / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")

    records = []
    errors = []
    for category, rel, path in files_for_audit(root):
        if len(records) >= limit:
            errors.append("Inventory file limit reached")
            break
        try:
            stat = path.stat()
            if stat.st_size > 20_000_000:
                errors.append("Skipping oversized source: " + rel)
                continue
            records.append({
                "category": category,
                "path": rel,
                "sha256": file_sha(path),
                "size_bytes": stat.st_size
            })
        except OSError:
            errors.append("Unable to inspect source: " + rel)

    revision = None
    try:
        cmd = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False
        )
        if cmd.returncode == 0:
            revision = cmd.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass

    plan = {
        "schema_version": 1,
        "run_id": folder.name,
        "mode": mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repository_revision": revision,
        "scope": [
            "bootstrap", "story-verifier", "regression-author",
            "regression-selector", "regression-runner",
            "cross-component"
        ],
        "source_count": len(records),
        "status": "draft",
        "limitations": errors,
        "approval": {
            "challenge_authorized": False,
            "disposable_environment_confirmed": False
        }
    }
    write_json(folder / "audit-plan.json", plan)
    write_json(folder / "evidence-index.json", {
        "schema_version": 1,
        "run_id": folder.name,
        "sources": records,
        "collection_errors": errors
    })
    write_json(folder / "findings.json", {
        "schema_version": 1, "run_id": folder.name, "findings": []
    })
    write_json(folder / "metrics.json", {
        "schema_version": 1, "run_id": folder.name,
        "metrics": {}, "benchmark_ids": [],
        "benchmark_fingerprints": {}, "limitations": [
            "No labeled metrics have been evaluated yet"
        ]
    })
    (folder / "audit-report.md").write_text(
        "# Veris Audit Report\n\n"
        "Overall verdict: DRAFT\n\n"
        "Scope: pending review\n\n"
        "Evidence and limitations: pending review\n\n"
        "Findings and next actions: pending review\n",
        encoding="utf-8"
    )
    return {
        "run_id": folder.name,
        "run_directory": str(folder),
        "source_count": len(records),
        "collection_errors": errors
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--mode", choices=["audit", "benchmark", "incident", "challenge"],
                   default="audit")
    p.add_argument("--max-sources", type=int, default=3000)
    args = p.parse_args()
    try:
        if args.max_sources < 1:
            raise ValueError("max-sources must be positive")
        print(json.dumps(
            initialize(Path(args.root), args.mode, args.max_sources), indent=2
        ))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print("Evidence collection failed: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
