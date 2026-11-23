#!/usr/bin/env python3
"""Shared helpers for Veris Regression Selector. Python 3.9+."""
import fnmatch
import hashlib
import json
import re
from pathlib import Path

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
LEVELS = ("targeted", "suite", "broad", "full")


def load(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected JSON object: " + str(path))
    return value


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_id(value):
    return isinstance(value, str) and bool(ID.fullmatch(value))


def inside(path, base):
    return Path(path).resolve().is_relative_to(Path(base).resolve())


def project_path(root, relative):
    path = Path(relative)
    if path.is_absolute():
        raise ValueError("Absolute project path not allowed")
    found = (Path(root) / path).resolve()
    if not inside(found, root):
        raise ValueError("Path escapes project: " + str(relative))
    return found


def matched(path, pattern):
    # Support git-like ** directory prefixes and ordinary globbing.
    path = path.replace("\\", "/")
    pattern = pattern.replace("\\", "/")
    if pattern.endswith("/**"):
        return path.startswith(pattern[:-3] + "/")
    return fnmatch.fnmatchcase(path, pattern)


def catalog_cases(root):
    path = Path(root) / ".veris" / "regression" / "catalog.json"
    doc = load(path)
    if doc.get("schema_version") != 1 or not isinstance(doc.get("cases"), list):
        raise ValueError("Invalid regression catalog schema")
    cases = {}
    for item in doc["cases"]:
        if not isinstance(item, dict) or not safe_id(item.get("id")):
            raise ValueError("Invalid catalog case")
        cid = item["id"]
        if cid in cases:
            raise ValueError("Duplicate catalog ID: " + cid)
        if not safe_id(item.get("suite")) or item.get("risk") not in {
            "critical", "high", "medium", "low"
        }:
            raise ValueError("Invalid suite/risk for case " + cid)
        test_file = project_path(root, item.get("test_file", ""))
        metadata_path = project_path(root, item.get("metadata_path", ""))
        if not test_file.is_file() or not metadata_path.is_file():
            raise ValueError("Missing test file or case metadata: " + cid)
        meta = load(metadata_path)
        if meta.get("id") != cid or meta.get("status") != "ready":
            raise ValueError("Catalog case not READY: " + cid)
        if meta.get("test", {}).get("file") != item.get("test_file"):
            raise ValueError("Test path differs from case metadata: " + cid)
        if (meta.get("coverage", {}).get("suite") != item.get("suite")):
            raise ValueError("Suite differs from case metadata: " + cid)
        cases[cid] = item
    return path, cases


def policy_load(root):
    path = Path(root) / ".veris" / "regression" / "selection-policy.json"
    doc = load(path)
    if doc.get("schema_version") != 1:
        raise ValueError("Invalid selection policy version")
    for cid in doc.get("always_run_case_ids", []):
        if not safe_id(cid):
            raise ValueError("Invalid always-run case ID")
    for rule in doc.get("mandatory_rules", []):
        if not isinstance(rule, dict) or not safe_id(rule.get("id")):
            raise ValueError("Invalid mandatory rule ID")
        if not isinstance(rule.get("path_globs"), list):
            raise ValueError("Rule must contain path_globs")
        if not isinstance(rule.get("required_case_ids"), list):
            raise ValueError("Rule must contain required_case_ids")
    return path, doc


def mandatory(policy, paths):
    required = set(policy.get("always_run_case_ids", []))
    triggered = []
    for rule in policy.get("mandatory_rules", []):
        if any(matched(p, g) for p in paths
               for g in rule.get("path_globs", [])):
            triggered.append(rule["id"])
            required.update(rule.get("required_case_ids", []))
    return required, sorted(triggered)


def breadth_max(a, b):
    return LEVELS[max(LEVELS.index(a), LEVELS.index(b))]
