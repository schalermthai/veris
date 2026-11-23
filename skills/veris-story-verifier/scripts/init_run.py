#!/usr/bin/env python3
"""Create a unique story run with templates, no previous-run overwrites."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

MODES = {"targeted", "retest", "final"}
STORY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
CRITERION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def git_info(root):
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False
        )
        if head.returncode != 0:
            return None, None
        changed = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5, check=False
        )
        dirty = bool(changed.stdout.strip()) if changed.returncode == 0 else None
        return head.stdout.strip(), dirty
    except (OSError, subprocess.TimeoutExpired):
        return None, None


def parse_criteria(items):
    criteria = []
    ids = set()
    for item in items:
        if "=" not in item:
            raise ValueError("--ac must use ID=Description")
        identifier, description = item.split("=", 1)
        identifier, description = identifier.strip(), description.strip()
        if not CRITERION_RE.fullmatch(identifier) or not description:
            raise ValueError("Invalid criterion: " + item)
        if identifier in ids:
            raise ValueError("Duplicate criterion: " + identifier)
        ids.add(identifier)
        criteria.append({
            "id": identifier, "description": description, "required": True
        })
    return criteria


def safe_within(path, root):
    return path.resolve().is_relative_to(root.resolve())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--story", required=True)
    parser.add_argument("--mode", choices=sorted(MODES), default="final")
    parser.add_argument("--ac", action="append", default=[],
                        help="Acceptance criterion formatted ID=Description")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        parser.error("Root directory does not exist")
    if not STORY_RE.fullmatch(args.story) or args.story in {".", ".."}:
        parser.error("Story ID must be an ordinary path-safe identifier")

    try:
        criteria = parse_criteria(args.ac)
        profile = root / ".veris" / "verification-profile.yaml"
        playbook = root / ".veris" / "verification-playbook.md"
        if not profile.is_file() or not playbook.is_file():
            raise ValueError("Bootstrap profile and playbook are required")
        story_dir = root / ".veris" / "stories" / args.story
        if not safe_within(story_dir, root):
            raise ValueError("Story output path escapes repository")
        runs = story_dir / "runs"
        runs.mkdir(parents=True, exist_ok=True)

        directory = None
        for index in range(1, 100001):
            candidate = runs / ("run-%04d" % index)
            try:
                candidate.mkdir(exist_ok=False)
                directory = candidate
                break
            except FileExistsError:
                continue
        if directory is None:
            raise ValueError("Unable to allocate a unique run ID")

        (directory / "evidence").mkdir()
        asset_dir = Path(__file__).resolve().parent.parent / "assets"
        for source, target in [
            ("verification-plan.md", "verification-plan.md"),
            ("verification-report.md", "verification-report.md")
        ]:
            text = (asset_dir / source).read_text(encoding="utf-8")
            (directory / target).write_text(text, encoding="utf-8")

        head, dirty = git_info(root)
        bootstrap_status = "unknown"
        try:
            from check_context import inspect
            bootstrap_status = inspect(root)["bootstrap_status"]
        except (ImportError, OSError):
            pass

        result = {
            "schema_version": 1,
            "story_id": args.story,
            "run_id": directory.name,
            "mode": args.mode,
            "implementation_revision": head,
            "worktree_dirty_at_start": dirty,
            "bootstrap_status": bootstrap_status,
            "overall_verdict": "blocked",
            "criteria": criteria,
            "scenarios": [],
            "defects": [],
            "unexpected_findings": [],
            "environment_findings": [],
            "regression_candidates": [],
            "next_action": "Plan and execute verification"
        }
        results_path = directory / "results.json"
        results_path.write_text(json.dumps(result, indent=2) + "\n",
                                encoding="utf-8")
        print(json.dumps({
            "story_id": args.story,
            "run_id": directory.name,
            "mode": args.mode,
            "run_directory": str(directory),
            "plan": str(directory / "verification-plan.md"),
            "report": str(directory / "verification-report.md"),
            "results": str(results_path),
            "evidence_directory": str(directory / "evidence"),
            "implementation_revision": head,
            "worktree_dirty_at_start": dirty
        }, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print("Veris initialization error: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
