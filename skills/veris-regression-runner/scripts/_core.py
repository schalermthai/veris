#!/usr/bin/env python3
"""Common Veris runner validation and planning helpers.

Standard library only. Does not run E2E tests or invoke Docker.
"""
import fnmatch
import hashlib
import json
import re
import subprocess
from pathlib import Path

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
CASE_STATES = {
    "pass", "fail", "blocked", "infra_error",
    "inconclusive", "flaky", "not_run"
}
VERDICTS = {"passed", "failed", "blocked", "inconclusive"}


def load(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("Expected JSON object: " + str(path))
    return doc


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inside(path, root):
    return Path(path).resolve().is_relative_to(Path(root).resolve())


def root_file(root, value, required=True):
    if not isinstance(value, str) or not value:
        raise ValueError("Missing relative file path")
    p = Path(value)
    if p.is_absolute():
        raise ValueError("Absolute project path is prohibited")
    full = (root / p).resolve()
    if not inside(full, root):
        raise ValueError("Project path escapes root")
    if required and not full.is_file():
        raise ValueError("File missing: " + value)
    return full


def git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=30, check=False
    )
    if result.returncode:
        raise ValueError("Git command failed: " + " ".join(args))
    return result.stdout


def match_path(path, pattern):
    if pattern.endswith("/**"):
        return path.startswith(pattern[:-3] + "/")
    return fnmatch.fnmatchcase(path, pattern)


def permitted_untracked(path):
    return path.startswith((
        ".veris/regression/executions/",
        ".veris/regression/selections/",
        ".veris/runtime-instances/"
    ))


def ensure_clean(root):
    tracked = git(root, "status", "--porcelain", "--untracked-files=no")
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z")
    unknown = [
        p for p in untracked.decode("utf-8", "replace").split("\0")
        if p and not permitted_untracked(p)
    ]
    if tracked.strip() or unknown:
        raise ValueError(
            "Source checkout is dirty or has untracked nonexecution files. "
            "Use a clean immutable checkout. Untracked: " +
            ", ".join(unknown[:10])
        )


def commands_for(case, metadata, runtime, policy):
    test = metadata.get("test", {})
    if test.get("kind") != "deterministic-e2e":
        raise ValueError(
            "Hybrid/agentic test needs an approved custom adapter: " + case["id"]
        )
    framework = test.get("framework")
    adapters = policy.get("test_adapters", {})
    adapter = adapters.get(framework)
    if not isinstance(adapter, dict) or adapter.get("enabled") is not True:
        raise ValueError("Unsupported framework for case " + case["id"])
    executable = adapter.get("executable")
    if executable not in runtime.get("allowed_executables", []):
        raise ValueError(
            "Runtime allowed_executables missing " + str(executable)
        )
    file = test.get("file")
    if file != case.get("test_file"):
        raise ValueError("Test file differs from catalog for " + case["id"])
    if framework == "playwright":
        if not file.endswith((".spec.ts", ".spec.js", ".test.ts", ".test.js")):
            raise ValueError("Unexpected Playwright file extension")
        return [executable, "test", file, "--reporter=json"]
    if framework == "pytest":
        if not file.endswith(".py"):
            raise ValueError("Unexpected pytest file extension")
        return [executable, file, "-q"]
    raise ValueError("Framework adapter not implemented: " + str(framework))


def check_inputs(root, selection_path, verify_git=True):
    root = Path(root).resolve()
    selection_path = Path(selection_path).resolve()
    if not inside(selection_path, root):
        raise ValueError("Selection must be inside project")
    sel = load(selection_path)
    if sel.get("schema_version") != 1:
        raise ValueError("Unsupported selection schema")
    if sel.get("status") != "ready_for_runner":
        raise ValueError("Selection not ready_for_runner")
    if not SAFE_ID.fullmatch(str(sel.get("change_id", ""))):
        raise ValueError("Invalid change ID")

    registry_path = root / ".veris/regression/catalog.json"
    policy_path = root / ".veris/regression/selection-policy.json"
    exec_policy_path = root / ".veris/regression/execution-policy.json"
    registry = load(registry_path)
    selector_policy = load(policy_path)
    policy = load(exec_policy_path)
    if registry.get("schema_version") != 1:
        raise ValueError("Unsupported catalog schema")
    if selector_policy.get("schema_version") != 1:
        raise ValueError("Unsupported selector policy")
    if policy.get("schema_version") != 1:
        raise ValueError("Unsupported execution policy")
    if digest(registry_path) != sel.get("catalog_sha256"):
        raise ValueError("Catalog changed since selection")
    if digest(policy_path) != sel.get("policy_sha256"):
        raise ValueError("Selector policy changed since selection")

    source = sel.get("source", {})
    changes_file = root_file(root, source.get("changes_file"))
    changes = load(changes_file)
    if changes.get("change_id") != sel.get("change_id"):
        raise ValueError("Change ID mismatch")
    for field in ("base_revision", "head_revision", "diff_sha256"):
        if changes.get(field) != source.get(field):
            raise ValueError("Change source mismatch: " + field)
    if changes.get("worktree_dirty") is True:
        raise ValueError("Selection was produced from a dirty checkout")
    if changes.get("diff_truncated") and sel.get("breadth") != "full":
        raise ValueError("Truncated diff requires full selection")

    if verify_git:
        current = git(root, "rev-parse", "HEAD").decode().strip()
        if current != source.get("head_revision"):
            raise ValueError("Current HEAD differs from selected head revision")
        recomputed = git(
            root, "diff", "--no-ext-diff", "--no-textconv",
            "--find-renames", source["base_revision"],
            source["head_revision"], "--"
        )
        if hashlib.sha256(recomputed).hexdigest() != source.get("diff_sha256"):
            raise ValueError("Current diff digest differs from selection")
        if not policy.get("allow_dirty_worktree", False):
            ensure_clean(root)

    cases = registry.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Catalog cases must be an array")
    by_id = {}
    for item in cases:
        cid = item.get("id") if isinstance(item, dict) else None
        if not isinstance(cid, str) or cid in by_id:
            raise ValueError("Invalid or duplicate catalog ID")
        by_id[cid] = item

    selected = sel.get("selected_cases")
    excluded = sel.get("excluded_cases")
    if not isinstance(selected, list) or not isinstance(excluded, list):
        raise ValueError("Invalid selected/excluded case lists")
    ids = [c.get("id") for c in selected if isinstance(c, dict)]
    other = [c.get("id") for c in excluded if isinstance(c, dict)]
    if len(ids) != len(selected) or len(other) != len(excluded):
        raise ValueError("Invalid selected/excluded case entries")
    if len(ids) != len(set(ids)) or len(other) != len(set(other)):
        raise ValueError("Duplicate case IDs in selection")
    if (set(ids) | set(other)) != set(by_id) or (set(ids) & set(other)):
        raise ValueError("Selection does not account for catalog exactly")

    mandatory = set(selector_policy.get("always_run_case_ids", []))
    triggered = []
    changed = changes.get("changed_files", [])
    for rule in selector_policy.get("mandatory_rules", []):
        if any(match_path(p, g) for p in changed
               for g in rule.get("path_globs", [])):
            triggered.append(rule["id"])
            mandatory.update(rule.get("required_case_ids", []))
    if not mandatory.issubset(set(ids)):
        raise ValueError("Mandatory tests omitted")
    if set(sel.get("mandatory_case_ids", [])) != mandatory:
        raise ValueError("Mandatory list mismatch")
    if set(sel.get("triggered_rules", [])) != set(triggered):
        raise ValueError("Mandatory rule triggers mismatch")
    if sel.get("breadth") == "full" and set(ids) != set(by_id):
        raise ValueError("Full selection omitted cases")
    if sel.get("breadth") == "broad":
        required_high = {
            c["id"] for c in cases if c.get("risk") in {"critical", "high"}
        }
        if not required_high.issubset(set(ids)):
            raise ValueError("Broad selection omitted critical/high cases")
    for item in excluded:
        if item.get("reviewed_by") != "coding-agent" or not item.get("reason"):
            raise ValueError("Unreviewed exclusion")
    if sel.get("missing_mandatory_case_ids"):
        raise ValueError("Missing mandatory cases")

    profile = root / ".veris/verification-profile.yaml"
    playbook = root / ".veris/verification-playbook.md"
    sandbox_path = root / ".veris/sandbox/sandbox.yaml"
    adapter_path = root / ".veris/sandbox/runtime.py"
    for file in (profile, playbook, sandbox_path, adapter_path):
        if not file.is_file():
            raise ValueError("Missing Bootstrap dependency: " + str(file))
    profile_text = profile.read_text(encoding="utf-8")
    if (".veris/sandbox/runtime.py" not in profile_text or
        ".veris/sandbox/sandbox.yaml" not in profile_text):
        raise ValueError("Bootstrap profile must reference the shared runtime")

    sandbox = load(sandbox_path)
    runtime = sandbox.get("runtime", {})
    if sandbox.get("template_status") != "ready":
        raise ValueError("Bootstrap runtime template not READY")
    if runtime.get("provider") != "docker-compose":
        raise ValueError("Only Docker Compose runtime implemented in v1")
    if (policy.get("require_image_identity_enforcement", True) and
        runtime.get("enforce_image_identity") is not True):
        raise ValueError("Bootstrap image identity enforcement is required")
    if policy.get("strategy") != "serial-per-case":
        raise ValueError("v1 supports serial-per-case strategy only")
    if policy.get("max_parallel_cases") != 1:
        raise ValueError("v1 parallelism must be one")

    resolved = []
    for cid in ids:
        item = by_id[cid]
        meta_file = root_file(root, item.get("metadata_path"))
        meta = load(meta_file)
        if meta.get("id") != cid or meta.get("status") != "ready":
            raise ValueError("Case metadata invalid or not READY: " + cid)
        test_path = root_file(root, item.get("test_file"))
        if not test_path.is_file():
            raise ValueError("Test file missing for " + cid)
        argv = commands_for(item, meta, runtime, policy)
        resolved.append({
            "id": cid,
            "framework": meta["test"]["framework"],
            "kind": meta["test"]["kind"],
            "test_file": item["test_file"],
            "argv": argv
        })

    return {
        "root": root,
        "selection": sel,
        "selection_file": selection_path,
        "selection_hash": digest(selection_path),
        "execution_policy_hash": digest(exec_policy_path),
        "cases": resolved,
        "runtime_adapter": adapter_path,
        "sandbox": sandbox
    }


def computed_verdict(cases):
    if not cases:
        return "blocked"
    states = [c.get("status") for c in cases]
    if "fail" in states:
        return "failed"
    if any(x in {"blocked", "infra_error", "not_run"} for x in states):
        return "blocked"
    if any(x in {"inconclusive", "flaky"} for x in states):
        return "inconclusive"
    return "passed" if all(x == "pass" for x in states) else "inconclusive"


def summary(cases):
    out = {"selected": len(cases)}
    for state in ("pass", "fail", "blocked", "infra_error",
                  "inconclusive", "flaky", "not_run"):
        out[{"pass": "passed", "fail": "failed"}.get(state, state)] = sum(
            c.get("status") == state for c in cases
        )
    return out


def argv_for_test(case):
    return case["argv"]
