#!/usr/bin/env python3
"""Shared strict source validation for Veris Regression Author."""
import json
import re
from pathlib import Path

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def valid_id(value):
    return isinstance(value, str) and bool(ID_RE.fullmatch(value))


def good_text(value):
    return isinstance(value, str) and bool(value.strip())


def inside(path, directory):
    return path.resolve().is_relative_to(directory.resolve())


def read_json(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object: " + str(path))
    return data


def relative_file(root, value, must_exist=True):
    if not good_text(value):
        raise ValueError("Missing relative file path")
    supplied = Path(value)
    if supplied.is_absolute():
        raise ValueError("Absolute paths are not allowed: " + value)
    path = root / supplied
    if not inside(path, root):
        raise ValueError("Path escapes repository: " + value)
    if must_exist and (not path.is_file() or path.stat().st_size == 0):
        raise ValueError("Missing or empty file: " + value)
    return path


def check_story(root, source):
    root = root.resolve()
    source = source.resolve()
    story_base = root / ".veris" / "stories"
    errors = []
    if not inside(source, story_base) or source.name != "results.json":
        raise ValueError("Source must be a Veris story run results.json")
    if not source.is_file():
        raise ValueError("Source story results do not exist")
    doc = read_json(source)
    if doc.get("mode") != "final":
        errors.append("Source must be a final Story Verifier run")
    if doc.get("overall_verdict") != "verified":
        errors.append("Source must have overall_verdict=verified")
    if not good_text(doc.get("implementation_revision")):
        errors.append("Source must record implementation_revision")
    if not valid_id(doc.get("story_id")) or not valid_id(doc.get("run_id")):
        errors.append("Invalid story_id or run_id")
    if doc.get("run_id") != source.parent.name:
        errors.append("Source run ID does not match directory")
    if doc.get("story_id") != source.parent.parent.parent.name:
        errors.append("Source story ID does not match directory")
    criteria = doc.get("criteria")
    scenarios = doc.get("scenarios")
    if not isinstance(criteria, list) or not isinstance(scenarios, list):
        raise ValueError("Story must have criteria and scenarios arrays")
    required = set()
    criteria_seen = set()
    for c in criteria:
        if not isinstance(c, dict) or not valid_id(c.get("id")):
            errors.append("Invalid acceptance criterion")
            continue
        cid = c["id"]
        if cid in criteria_seen:
            errors.append("Duplicate acceptance criterion " + cid)
        criteria_seen.add(cid)
        if c.get("required") is True:
            required.add(cid)
    if not required:
        errors.append("Source has no required acceptance criteria")
    covered = set()
    found_scenarios = set()
    for s in scenarios:
        if not isinstance(s, dict) or not valid_id(s.get("id")):
            errors.append("Invalid scenario record")
            continue
        sid = s["id"]
        if sid in found_scenarios:
            errors.append("Duplicate scenario " + sid)
        found_scenarios.add(sid)
        if s.get("required") is not True:
            continue
        if s.get("status") != "pass":
            errors.append("Required scenario not PASS: " + sid)
            continue
        oracle = s.get("independent_check")
        if not isinstance(oracle, dict) or oracle.get("status") != "pass":
            errors.append("Missing passing independent checker: " + sid)
        if not good_text(s.get("actual")):
            errors.append("Missing actual observation: " + sid)
        evidence = s.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append("Missing scenario evidence: " + sid)
        else:
            for item in evidence:
                try:
                    path = source.parent / str(item)
                    if not inside(path, source.parent) or not path.is_file() or path.stat().st_size == 0:
                        errors.append("Invalid scenario evidence: " + sid)
                except (OSError, TypeError):
                    errors.append("Unreadable scenario evidence: " + sid)
        refs = s.get("criterion_ids")
        if not isinstance(refs, list) or not refs:
            errors.append("Scenario lacks criterion IDs: " + sid)
        else:
            for cid in refs:
                if cid not in criteria_seen:
                    errors.append("Unknown criterion reference: " + str(cid))
                else:
                    covered.add(cid)
    for cid in required - covered:
        errors.append("Required acceptance criterion not covered: " + cid)
    for d in doc.get("defects", []):
        if isinstance(d, dict) and d.get("blocking") is True and d.get("status") == "open":
            errors.append("Open blocking defect in source verification")
    return doc, errors
