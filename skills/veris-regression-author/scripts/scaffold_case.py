#!/usr/bin/env python3
"""Scaffold case metadata/plan from a verified story scenario."""
import argparse
import json
import sys
from pathlib import Path
from _common import check_story, inside, valid_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--source", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--suite", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not valid_id(args.case) or not valid_id(args.suite):
        parser.error("Case ID and suite must be path-safe identifiers")
    try:
        source = (root / args.source).resolve()
        doc, errors = check_story(root, source)
        if errors:
            raise ValueError("Invalid source: " + "; ".join(errors))
        selected = [
            s for s in doc["scenarios"] if s.get("id") == args.scenario
            and s.get("required") is True and s.get("status") == "pass"
        ]
        if len(selected) != 1:
            raise ValueError("Selected scenario must be one required PASS")
        s = selected[0]
        cases_dir = root / ".veris" / "regression" / "cases"
        plans_dir = root / ".veris" / "regression" / "plans"
        cases_dir.mkdir(parents=True, exist_ok=True)
        plans_dir.mkdir(parents=True, exist_ok=True)
        case_path = cases_dir / (args.case + ".json")
        plan_path = plans_dir / (args.case + ".md")
        if not inside(case_path, root) or not inside(plan_path, root):
            raise ValueError("Output path escapes repository")
        if case_path.exists() or plan_path.exists():
            raise ValueError("Existing case or plan; refuse to overwrite")
        result = {
            "schema_version": 1,
            "id": args.case,
            "title": s.get("name") or args.case,
            "status": "draft",
            "source": {
                "story_id": doc["story_id"],
                "run_id": doc["run_id"],
                "results_file": str(source.relative_to(root)),
                "revision": doc["implementation_revision"],
                "scenario_ids": [s["id"]],
                "criterion_ids": list(s.get("criterion_ids", []))
            },
            "coverage": {
                "suite": args.suite,
                "risk": "medium",
                "behaviors": [],
                "surfaces": [],
                "components": [],
                "api_routes": [],
                "tags": []
            },
            "test": {
                "file": None,
                "name": None,
                "framework": None,
                "kind": "deterministic-e2e",
                "command": None,
                "surface_actions": [],
                "assertions": [],
                "fixtures": [],
                "cleanup": None
            },
            "execution": {"runs": [], "notes": None},
            "maintenance": {"owner": None, "notes": None}
        }
        description = (
            "# Regression plan — " + args.case + "\n\n"
            + "Source story: " + doc["story_id"] + "\n\n"
            + "Source run: " + doc["run_id"] + "\n\n"
            + "Scenario: " + s["id"] + "\n\n"
            + "Business behavior: " + str(s.get("name") or "") + "\n\n"
            + "Expected: " + str(s.get("expected") or "") + "\n\n"
            + "Observed: " + str(s.get("actual") or "") + "\n\n"
            + "## Setup\n\n[TBD]\n\n## Driver\n\n[TBD]\n\n"
            + "## Independent assertions\n\n[TBD]\n\n"
            + "## Teardown\n\n[TBD]\n\n"
            + "## Stability and evidence\n\n[TBD]\n"
        )
        with case_path.open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
        try:
            with plan_path.open("x", encoding="utf-8") as f:
                f.write(description)
        except Exception:
            case_path.unlink(missing_ok=True)
            raise
        print(json.dumps({
            "case": args.case,
            "status": "draft",
            "metadata": str(case_path),
            "plan": str(plan_path),
            "source_story": doc["story_id"],
            "source_scenario": s["id"]
        }, indent=2))
        return 0
    except (OSError, ValueError, TypeError) as e:
        print("Scaffolding error: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
