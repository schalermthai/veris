#!/usr/bin/env python3
"""Shared offline helpers for the Veris Verification Auditor."""
import hashlib
import json
import os
import re
from pathlib import Path

RUN_RE = re.compile(r"^run-[0-9]{4,6}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
COMPONENTS = {
    "bootstrap", "story-verifier", "regression-author",
    "regression-selector", "regression-runner", "cross-component"
}
SEVERITIES = {"critical", "high", "medium", "low"}
CONFIDENCES = {"confirmed", "probable", "uncertain"}


def safe(root, value, must_exist=True):
    root = Path(root).resolve()
    rel = Path(value)
    if rel.is_absolute():
        raise ValueError("Absolute artifact path prohibited")
    path = (root / rel).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Artifact escapes repository")
    if must_exist and not path.is_file():
        raise ValueError("Missing artifact: " + str(value))
    return path


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path, max_bytes=5_000_000):
    path = Path(path)
    if path.stat().st_size > max_bytes:
        raise ValueError("JSON artifact exceeds size limit: " + str(path))
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("Expected JSON object: " + str(path))
    return doc


def write_json(path, obj):
    path = Path(path)
    if path.exists() and path.is_symlink():
        raise ValueError("Refusing symlink output")
    temp = path.with_suffix(path.suffix + ".tmp")
    if temp.exists():
        raise ValueError("Temporary audit output already exists")
    with temp.open("x", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(temp, path)


def is_run(root, path):
    root = Path(root).resolve()
    path = Path(path).resolve()
    parent = root / ".veris" / "audits" / "runs"
    if path.parent != parent or not RUN_RE.fullmatch(path.name):
        raise ValueError("Invalid audit run directory")
    if not path.is_dir():
        raise ValueError("Audit run does not exist")
    return path


def writable(run):
    if (run / "audit-seal.json").exists():
        raise ValueError("Audit is sealed; create a new run")


def fingerprint(*parts):
    payload = json.dumps(parts, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:20]


def finding(source, component, category, severity, summary, evidence,
            expected, observed, recommendation, validation, confidence="confirmed"):
    fp = fingerprint(component, category, summary, sorted(evidence))
    return {
        "id": source.upper() + "-" + fp[:10],
        "fingerprint": fp,
        "source": source,
        "component": component,
        "category": category,
        "severity": severity,
        "confidence": confidence,
        "status": "open",
        "summary": summary,
        "expected": expected,
        "observed": observed,
        "evidence": evidence,
        "recommendation": recommendation,
        "validation": validation
    }


def replace_findings(run, source, entries):
    writable(run)
    path = run / "findings.json"
    doc = read_json(path)
    others = [
        x for x in doc.get("findings", [])
        if isinstance(x, dict) and x.get("source") != source
    ]
    all_entries = others + entries
    doc["findings"] = sorted(
        all_entries, key=lambda x: (x.get("source", ""), x.get("id", ""))
    )
    write_json(path, doc)


def files_for_audit(root):
    root = Path(root)
    exact = [
        ("bootstrap", ".veris/verification-profile.yaml"),
        ("bootstrap", ".veris/verification-playbook.md"),
        ("bootstrap", ".veris/bootstrap-report.md"),
        ("bootstrap", ".veris/sandbox/sandbox.yaml"),
        ("regression-author", ".veris/regression/catalog.json"),
        ("regression-selector", ".veris/regression/selection-policy.json"),
        ("regression-runner", ".veris/regression/execution-policy.json"),
        ("auditor", ".veris/audits/policy.json")
    ]
    patterns = [
        ("bootstrap", ".veris/reports/run-*.md"),
        ("bootstrap", ".veris/evidence/run-*/results.json"),
        ("story-verifier", ".veris/stories/*/runs/*/results.json"),
        ("regression-author", ".veris/regression/cases/*.json"),
        ("regression-selector", ".veris/regression/selections/*/runs/*/selection.json"),
        ("regression-runner", ".veris/regression/executions/*/runs/*/results.json"),
        ("benchmark", ".veris/audits/benchmarks/*.json"),
        ("incident", ".veris/audits/incidents/*.json")
    ]
    seen = set()
    for category, rel in exact:
        path = root / rel
        if path.is_file() and not path.is_symlink():
            resolved = path.resolve()
            if resolved.is_relative_to(root.resolve()) and rel not in seen:
                seen.add(rel)
                yield category, rel, resolved
    for category, pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if not path.is_file() or path.is_symlink():
                continue
            resolved = path.resolve()
            rel = str(path.relative_to(root))
            if resolved.is_relative_to(root.resolve()) and rel not in seen:
                seen.add(rel)
                yield category, rel, resolved
