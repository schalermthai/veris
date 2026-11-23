#!/usr/bin/env python3
"""Collect immutable Git commit-to-commit diff metadata."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def git(root, *args):
    run = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, timeout=30, check=False
    )
    if run.returncode != 0:
        raise ValueError(run.stderr.decode("utf-8", "replace")[:1000])
    return run.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--change-id", required=True)
    ap.add_argument("--out")
    ap.add_argument("--max-preview-lines", type=int, default=1500)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    try:
        base = git(root, "rev-parse", "--verify", args.base + "^{commit}").decode().strip()
        head = git(root, "rev-parse", "--verify", args.head + "^{commit}").decode().strip()
        raw = git(root, "diff", "--no-ext-diff", "--no-textconv",
                  "--find-renames", base, head, "--")
        files = git(root, "diff", "--name-only", "-z", "--find-renames",
                    base, head, "--").decode("utf-8", "replace")
        names = sorted(set(x for x in files.split("\0") if x))
        dirty = bool(git(root, "status", "--porcelain", "--untracked-files=no").strip())
        text = raw.decode("utf-8", "replace")
        lines = text.splitlines()
        maxlines = max(0, args.max_preview_lines)
        truncated = len(lines) > maxlines
        doc = {
            "schema_version": 1,
            "change_id": args.change_id,
            "base_revision": base,
            "head_revision": head,
            "diff_sha256": hashlib.sha256(raw).hexdigest(),
            "changed_files": names,
            "diff_preview": "\n".join(lines[:maxlines]),
            "diff_truncated": truncated,
            "total_diff_lines": len(lines),
            "worktree_dirty": dirty,
            "includes_worktree": False,
            "notes": [
                "Commit-to-commit diff only; uncommitted changes are excluded."
            ] if dirty else []
        }
        output = json.dumps(doc, indent=2) + "\n"
        if args.out:
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as f:
                f.write(output)
            print(json.dumps({
                "changes_file": str(path),
                "changed_file_count": len(names),
                "diff_truncated": truncated,
                "worktree_dirty": dirty
            }, indent=2))
        else:
            print(output)
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        print("Change collection error: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
