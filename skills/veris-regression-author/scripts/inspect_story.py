#!/usr/bin/env python3
"""Inspect Story Verifier source eligibility; read-only."""
import argparse
import json
import sys
from pathlib import Path
from _common import check_story


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    source = (root / args.source).resolve()
    try:
        doc, errors = check_story(root, source)
        eligible = not errors
        result = {
            "eligible": eligible,
            "story_id": doc.get("story_id"),
            "run_id": doc.get("run_id"),
            "revision": doc.get("implementation_revision"),
            "criteria_count": len(doc.get("criteria", [])),
            "scenario_count": len(doc.get("scenarios", [])),
            "errors": errors,
            "note": "Record integrity is not proof that underlying evidence is truthful."
        }
        print(json.dumps(result, indent=2))
        return 0 if eligible else 1
    except (OSError, ValueError, TypeError) as e:
        print("Story inspection error: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
