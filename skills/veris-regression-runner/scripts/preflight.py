#!/usr/bin/env python3
"""Validate a selection and project runtime before provisioning."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from _core import check_inputs


def preflight(root, selection, with_docker=False):
    context = check_inputs(root, selection, verify_git=True)
    result = {
        "ready": True,
        "change_id": context["selection"]["change_id"],
        "selected_head": context["selection"]["source"]["head_revision"],
        "selected_count": len(context["cases"]),
        "selection_sha256": context["selection_hash"],
        "runtime_provider": "docker-compose",
        "case_adapters": sorted(set(c["framework"] for c in context["cases"])),
        "warnings": [],
        "errors": []
    }
    if not context["cases"]:
        result["ready"] = False
        result["errors"].append("No selected regression cases: no passing gate")
    if with_docker:
        completed = subprocess.run(
            [sys.executable, str(context["runtime_adapter"]),
             "--root", str(Path(root).resolve()), "validate", "--with-docker"],
            capture_output=True, text=True, timeout=60, check=False
        )
        if completed.returncode != 0:
            result["ready"] = False
            result["errors"].append(
                "Bootstrap Docker runtime validation failed; run Bootstrap harden"
            )
        docker = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=20, check=False
        )
        if docker.returncode:
            result["ready"] = False
            result["errors"].append("Docker daemon unavailable")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--selection", required=True)
    ap.add_argument("--with-docker", action="store_true")
    a = ap.parse_args()
    try:
        result = preflight(Path(a.root).resolve(),
                           Path(a.selection).resolve(), a.with_docker)
        print(json.dumps(result, indent=2))
        return 0 if result["ready"] else 1
    except (OSError, ValueError, KeyError, TypeError,
            subprocess.TimeoutExpired) as error:
        print(json.dumps({
            "ready": False,
            "errors": [str(error)]
        }, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
