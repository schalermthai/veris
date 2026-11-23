#!/usr/bin/env python3
"""Check Veris bootstrap context without modifying the repository.

Python 3.9+, standard library only. This performs a lightweight
file/known-field check, not full YAML schema validation.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def nested_scalar(source, section, key):
    """Read a simple 2-space-indented YAML scalar, without parsing YAML."""
    inside = False
    for line in source.splitlines():
        if re.match(r"^[A-Za-z][\w-]*:\s*(?:#.*)?$", line):
            inside = line.split(":", 1)[0] == section
            continue
        if not inside:
            continue
        if re.match(r"^\S", line):
            inside = False
            continue
        found = re.match(r"^  " + re.escape(key) + r":\s*([^#]*)", line)
        if found:
            value = found.group(1).strip().strip("'\"")
            return value if value and value != "null" else None
    return None


def inspect(root, strict=False):
    veris = root / ".veris"
    paths = {
        "profile": veris / "verification-profile.yaml",
        "playbook": veris / "verification-playbook.md",
        "report": veris / "bootstrap-report.md",
        "reports_directory": veris / "reports",
        "sandbox_directory": veris / "sandbox"
    }
    present = {name: p.is_file() if name in {"profile", "playbook", "report"}
               else p.is_dir() for name, p in paths.items()}
    warnings = []
    errors = []
    status = "missing"
    handoff_ready = None

    if not present["profile"]:
        errors.append("Missing .veris/verification-profile.yaml")
    if not present["playbook"]:
        errors.append("Missing .veris/verification-playbook.md")
    if not present["report"]:
        warnings.append("Latest bootstrap report unavailable")

    if present["profile"]:
        try:
            content = paths["profile"].read_text(encoding="utf-8")
            status = (nested_scalar(content, "bootstrap", "status")
                      or "unknown").lower()
            handoff_ready = nested_scalar(
                content, "handoff", "story_verifier_ready"
            )
            if status not in {"ready", "partial", "blocked"}:
                warnings.append("Bootstrap status unknown or unrecognized")
            if handoff_ready == "false":
                warnings.append("Bootstrap handoff does not mark story verifier ready")
            # This is a hint only. Full YAML semantics require an agent or
            # an independent YAML parser.
        except (OSError, UnicodeError) as exc:
            errors.append("Cannot read bootstrap profile: " + str(exc))

    if status in {"blocked", "unknown", "missing"}:
        warnings.append("Do not assume end-to-end verification readiness")
    if strict and (status != "ready" or handoff_ready == "false"):
        errors.append("Strict mode requires ready bootstrap and enabled handoff")

    return {
        "root": str(root),
        "bootstrap_status": status,
        "story_verifier_ready": handoff_ready,
        "present": present,
        "paths": {k: str(v) for k, v in paths.items()},
        "warnings": warnings,
        "errors": errors,
        "usable": not errors
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        parser.error("Root directory not found")
    result = inspect(root, args.strict)
    print(json.dumps(result, indent=2))
    return 0 if result["usable"] else 1


if __name__ == "__main__":
    sys.exit(main())
