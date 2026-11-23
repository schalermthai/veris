#!/usr/bin/env python3
"""Publish a validated ready regression case into a stable catalog."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from _common import inside, read_json
from validate_case import validate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--case", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    case_path = (root / args.case).resolve()
    try:
        doc, errors, _ = validate(root, case_path)
        if errors:
            raise ValueError("Case invalid: " + "; ".join(errors))
        if doc.get("status") != "ready":
            raise ValueError("Only ready cases can be published")
        catalog_path = root / ".veris" / "regression" / "catalog.json"
        if not inside(catalog_path, root):
            raise ValueError("Catalog path escapes repository")
        if catalog_path.exists():
            catalog = read_json(catalog_path)
            if catalog.get("schema_version") != 1 or not isinstance(catalog.get("cases"), list):
                raise ValueError("Invalid existing regression catalog")
        else:
            catalog = {"schema_version": 1, "cases": []}
        case_id = doc["id"]
        test_file = doc["test"]["file"]
        for existing in catalog["cases"]:
            if existing.get("id") == case_id:
                raise ValueError("Case ID already published; review update explicitly")
            if existing.get("test_file") == test_file:
                raise ValueError("Executable test file already represented by another case")
        runs = doc["execution"]["runs"]
        latest_pass = next((r["id"] for r in reversed(runs) if r.get("status") == "pass"), None)
        entry = {
            "id": case_id,
            "suite": doc["coverage"]["suite"],
            "metadata_path": str(case_path.relative_to(root)),
            "test_file": test_file,
            "framework": doc["test"]["framework"],
            "kind": doc["test"]["kind"],
            "risk": doc["coverage"]["risk"],
            "behaviors": doc["coverage"]["behaviors"],
            "surfaces": doc["coverage"]["surfaces"],
            "components": doc["coverage"]["components"],
            "api_routes": doc["coverage"]["api_routes"],
            "tags": doc["coverage"]["tags"],
            "source_story": doc["source"]["story_id"],
            "source_revision": doc["source"]["revision"],
            "latest_run_id": latest_pass
        }
        catalog["cases"].append(entry)
        catalog["cases"].sort(key=lambda x: x["id"])
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".catalog-", suffix=".tmp", dir=catalog_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(catalog, f, indent=2)
                f.write("\n")
            os.replace(temp_name, catalog_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        print(json.dumps({
            "published": True,
            "case_id": case_id,
            "catalog": str(catalog_path),
            "total_cases": len(catalog["cases"])
        }, indent=2))
        return 0
    except (OSError, ValueError, TypeError) as e:
        print("Catalog publication error: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
