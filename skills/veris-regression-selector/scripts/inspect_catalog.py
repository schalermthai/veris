#!/usr/bin/env python3
"""Validate basic regression catalog registration integrity."""
import argparse
import json
import sys
from pathlib import Path
from _common import catalog_cases, digest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    try:
        path, cases = catalog_cases(Path(args.root).resolve())
        output = {
            "valid": True,
            "path": str(path),
            "sha256": digest(path),
            "case_count": len(cases),
            "suites": sorted(set(c["suite"] for c in cases.values())),
            "case_ids": sorted(cases)
        }
        print(json.dumps(output, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as e:
        print(json.dumps({"valid": False, "error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
