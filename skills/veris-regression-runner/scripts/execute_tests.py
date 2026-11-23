#!/usr/bin/env python3
"""Execute selected deterministic tests using Bootstrap v1.2 runtime.

One disposable Docker Compose instance per case, serial execution.
No automatic retries, implicit image build, or raw catalog command use.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from _core import (check_inputs, load, digest, inside,
                   computed_verdict, summary)
from preflight import preflight


def utc():
    return datetime.now(timezone.utc).isoformat()


def call_runtime(adapter, root, action, *args, timeout=420):
    proc = subprocess.run(
        [sys.executable, str(adapter), "--root", str(root), action, *args],
        capture_output=True, text=True, timeout=timeout, check=False
    )
    value = None
    try:
        value = json.loads(proc.stdout.strip())
    except (ValueError, TypeError):
        pass
    return proc.returncode, value, proc.stderr.strip()


def collect_copy(root, rel, case_dir):
    src = (root / rel).resolve()
    runtime_storage = root / ".veris" / "runtime-instances"
    if not inside(src, runtime_storage) or not src.is_file():
        raise ValueError("Untrusted or missing runtime evidence path")
    dst = case_dir / src.name
    shutil.copy2(src, dst)
    return str(dst.relative_to(case_dir.parent.parent))


def interpret(framework, stdout, exit_code):
    if exit_code != 0:
        return "inconclusive", "Test command failed; needs triage"
    if framework == "playwright":
        try:
            data = json.loads(stdout)
            stats = data["stats"]
            count = stats.get("expected", 0)
            invalid = (
                stats.get("unexpected", 0) or
                stats.get("flaky", 0) or
                stats.get("skipped", 0)
            )
            if (isinstance(count, int) and count > 0 and
                not invalid and not data.get("errors")):
                return "pass", "Playwright JSON reporter confirmed tests"
            return "inconclusive", "Zero, skipped, flaky, or failing Playwright tests"
        except (ValueError, KeyError, TypeError, AttributeError):
            return "inconclusive", "Playwright JSON result unavailable/invalid"
    if framework == "pytest":
        matched = re.search(r"(?<!\\d)([1-9][0-9]*) passed", stdout)
        if matched and "failed" not in stdout.lower():
            return "pass", "pytest reported one or more passed tests"
        return "inconclusive", "pytest outcome could not be verified"
    return "blocked", "Unsupported framework"


def save_results(path, data):
    data["summary"] = summary(data["cases"])
    data["overall_verdict"] = computed_verdict(data["cases"])
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def run_case(root, adapter, case, folder, selected_revision):
    cid = case["id"]
    case_dir = folder / "evidence" / cid
    case_dir.mkdir(parents=True, exist_ok=True)
    argv_path = case_dir / "argv.json"
    argv_path.write_text(json.dumps(case["argv"], indent=2) + "\n",
                         encoding="utf-8")
    result = {
        "id": cid,
        "status": "blocked",
        "attempts": [],
        "cleanup": "not_run",
        "triage": None,
        "notes": ""
    }
    instance = None
    start = time.monotonic()
    attempt = {
        "attempt": 1,
        "started_at": utc(),
        "status": "blocked",
        "exit_code": None,
        "evidence": [],
        "instance_id": None
    }
    try:
        rc, data, err = call_runtime(
            adapter, root, "provision",
            "--owner", "regression-" + cid,
            "--revision", selected_revision
        )
        if rc or not data or not data.get("instance"):
            raise RuntimeError("Provision failed: " + err[:300])
        instance = data["instance"]
        attempt["instance_id"] = instance

        rc, data, err = call_runtime(
            adapter, root, "start", "--instance", instance
        )
        if rc:
            raise RuntimeError("Runtime start failed: " + err[:300])

        rc, data, err = call_runtime(
            adapter, root, "healthcheck", "--instance", instance
        )
        if rc or not data or data.get("healthy") is not True:
            raise RuntimeError("Runtime not healthy: " + err[:300])

        rc, data, err = call_runtime(
            adapter, root, "execute", "--instance", instance,
            "--argv-file", str(argv_path.relative_to(root)),
            timeout=450
        )
        if data is None or "exit_code" not in data:
            raise RuntimeError("Execute command did not return a result")

        attempt["exit_code"] = data["exit_code"]
        for key in ("stdout_file", "stderr_file"):
            if data.get(key):
                attempt["evidence"].append(
                    collect_copy(root, data[key], case_dir)
                )
        stdout_file = case_dir / Path(data["stdout_file"]).name
        stdout = stdout_file.read_text(encoding="utf-8", errors="replace")
        label, explanation = interpret(
            case["framework"], stdout, data["exit_code"]
        )
        result["status"] = label
        attempt["status"] = label
        result["notes"] = explanation
        if rc not in (0, 1):
            result["status"] = "inconclusive"
            attempt["status"] = "inconclusive"
            result["notes"] = "Runtime command returned unexpected adapter status"
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
        result["status"] = "infra_error" if instance else "blocked"
        attempt["status"] = result["status"]
        result["notes"] = str(e)[:500]
    finally:
        if instance:
            try:
                rc, data, err = call_runtime(
                    adapter, root, "collect", "--instance", instance,
                    "--tail", "300"
                )
                if rc == 0 and data and data.get("logs"):
                    attempt["evidence"].append(
                        collect_copy(root, data["logs"], case_dir)
                    )
            except (OSError, ValueError, RuntimeError,
                    subprocess.TimeoutExpired):
                pass
            try:
                rc, data, err = call_runtime(
                    adapter, root, "destroy", "--instance", instance
                )
                result["cleanup"] = (
                    "pass" if rc == 0 and data and
                    (data.get("destroyed") or data.get("already_destroyed"))
                    else "fail"
                )
            except (OSError, ValueError, RuntimeError,
                    subprocess.TimeoutExpired):
                result["cleanup"] = "fail"
            if result["cleanup"] != "pass":
                result["status"] = "infra_error"
                attempt["status"] = "infra_error"
                result["notes"] += "; runtime cleanup failed"
        attempt["ended_at"] = utc()
        attempt["duration_ms"] = int(
            (time.monotonic() - start) * 1000
        )
        result["attempts"].append(attempt)
    return result


def execute(root, plan_path, only):
    plan = load(plan_path)
    results_path = plan_path.parent / "results.json"
    results = load(results_path)
    selection = root / plan["selection_file"]
    context = check_inputs(root, selection, verify_git=True)
    state = preflight(root, selection, with_docker=True)
    if not state["ready"]:
        raise ValueError("Preflight not ready: " + "; ".join(state["errors"]))
    if (plan.get("selection_sha256") != context["selection_hash"]
        or plan.get("head_revision") !=
        context["selection"]["source"]["head_revision"]):
        raise ValueError("Plan source is stale")
    if plan.get("execution_policy_sha256") != context["execution_policy_hash"]:
        raise ValueError("Execution policy has changed")
    if plan.get("cases") != context["cases"]:
        raise ValueError("Plan cases differ from validated selection")
    if (results.get("run_id") != plan.get("run_id") or
        results.get("selection_sha256") != plan.get("selection_sha256")):
        raise ValueError("Results and plan do not match")
    if any(c.get("attempts") for c in results["cases"]):
        raise ValueError("Already attempted run cannot be overwritten")

    case_ids = {c["id"] for c in plan["cases"]}
    if not set(only).issubset(case_ids):
        raise ValueError("Requested retest case not in selection")
    results["mode"] = "retest" if only else "run"
    adapter = context["runtime_adapter"]
    for case in plan["cases"]:
        if only and case["id"] not in only:
            continue
        output = run_case(
            root, adapter, case, plan_path.parent,
            plan["head_revision"]
        )
        for i, prior in enumerate(results["cases"]):
            if prior["id"] == case["id"]:
                results["cases"][i] = output
                break
        save_results(results_path, results)
    save_results(results_path, results)
    return {
        "run_id": results["run_id"],
        "verdict": results["overall_verdict"],
        "summary": results["summary"],
        "results": str(results_path)
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--case", action="append", default=[])
    a = ap.parse_args()
    root = Path(a.root).resolve()
    try:
        result = execute(root, Path(a.plan).resolve(), a.case)
        print(json.dumps(result, indent=2))
        return 0 if result["verdict"] == "passed" else 1
    except (OSError, ValueError, TypeError, RuntimeError,
            subprocess.TimeoutExpired, KeyError) as error:
        print("Execution error: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
