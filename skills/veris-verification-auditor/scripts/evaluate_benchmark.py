#!/usr/bin/env python3
"""Score independently labeled historical outcomes; never runs tests."""
import argparse
import json
import sys
from pathlib import Path
from _common import (
    is_run, writable, safe, read_json, file_sha,
    finding, replace_findings, write_json
)

KINDS = {"selection", "story-verdict", "runner-verdict"}


def metric(n, d):
    return {
        "numerator": n,
        "denominator": d,
        "value": (n / d if d else None)
    }


def evaluate(root):
    bench_dir = root / ".veris/audits/benchmarks"
    records, errors, findings = [], [], []
    totals = {
        "selection_recall": [0, 0],
        "selection_precision": [0, 0],
        "known_defect_detection_recall": [0, 0],
        "false_rejection_rate": [0, 0]
    }
    fingerprints = {}

    for path in sorted(bench_dir.glob("*.json")):
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("Unsafe benchmark path")
            bench = read_json(path)
            bid = bench.get("id")
            kind = bench.get("kind")
            truth = bench.get("ground_truth", {})
            if kind not in KINDS or bench.get("schema_version") != 1:
                raise ValueError("Invalid benchmark kind or schema")
            if (not isinstance(bid, str) or not bid
                or not isinstance(truth, dict)
                or truth.get("status") != "confirmed"
                or not isinstance(truth.get("reviewer"), str)
                or not truth["reviewer"].strip()):
                raise ValueError("No independently confirmed ground truth")
            evidence = truth.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                raise ValueError("Ground-truth evidence is required")
            for ref in evidence:
                if not safe(root, ref).is_file():
                    raise ValueError("Ground-truth evidence missing")
            observed_path = safe(root, bench.get("observed_file"))
            observed = read_json(observed_path)
            expected = bench.get("expected", {})
            if not isinstance(expected, dict):
                raise ValueError("Missing expected outcome")
            record = {
                "id": bid, "kind": kind,
                "benchmark_sha256": file_sha(path),
                "observed_file": bench["observed_file"],
                "ground_truth_evidence": evidence
            }

            if kind == "selection":
                relevant = expected.get("relevant_case_ids")
                if (not isinstance(relevant, list) or
                    not all(isinstance(x, str) for x in relevant) or
                    len(relevant) != len(set(relevant))):
                    raise ValueError("Invalid relevant case IDs")
                selected = {
                    x.get("id") for x in observed.get("selected_cases", [])
                    if isinstance(x, dict)
                }
                missed = sorted(set(relevant) - selected)
                selected_relevant = len(set(relevant) & selected)
                totals["selection_recall"][0] += selected_relevant
                totals["selection_recall"][1] += len(relevant)
                record["relevant_selected"] = selected_relevant
                record["relevant_total"] = len(relevant)
                record["missed_case_ids"] = missed
                record["outcome"] = "match" if not missed else "miss"
                if truth.get("complete_labels") is True:
                    universe = expected.get("eligible_case_ids")
                    if (not isinstance(universe, list) or not universe
                        or not set(relevant).issubset(set(universe))
                        or not selected.issubset(set(universe))):
                        raise ValueError("Invalid fully labeled eligible universe")
                    totals["selection_precision"][0] += selected_relevant
                    totals["selection_precision"][1] += len(selected)
                if missed:
                    findings.append(finding(
                        "benchmark", "regression-selector", "missing_coverage",
                        "high", "Labeled relevant regression cases omitted: " + bid,
                        [str(path.relative_to(root)), bench["observed_file"]],
                        "All labeled relevant cases selected", str(missed),
                        "Improve selector dependencies or mandatory rules",
                        "Reselect the same labeled PR and measure recall"
                    ))
            else:
                label = expected.get("verdict")
                actual = observed.get("overall_verdict")
                allowed = (
                    {"verified", "failed", "partial", "blocked"}
                    if kind == "story-verdict"
                    else {"passed", "failed", "blocked", "inconclusive"}
                )
                if label not in allowed or actual not in allowed:
                    raise ValueError("Invalid expected or observed verdict")
                record["expected_verdict"] = label
                record["observed_verdict"] = actual
                record["outcome"] = "match" if label == actual else "mismatch"
                if label == "failed":
                    totals["known_defect_detection_recall"][1] += 1
                    if actual == "failed":
                        totals["known_defect_detection_recall"][0] += 1
                if label in {"verified", "passed"}:
                    totals["false_rejection_rate"][1] += 1
                    if actual == "failed":
                        totals["false_rejection_rate"][0] += 1
                if actual != label:
                    component = ("story-verifier" if kind == "story-verdict"
                                 else "regression-runner")
                    findings.append(finding(
                        "benchmark", component, "inconsistent_verdict",
                        "high", "Labeled verdict mismatch: " + bid,
                        [str(path.relative_to(root)), bench["observed_file"]],
                        label, actual, "Investigate evidence and verifier gate",
                        "Replay the same labeled case under controlled conditions"
                    ))
            records.append(record)
            if bid in fingerprints:
                raise ValueError("Duplicate benchmark ID: " + bid)
            fingerprints[bid] = file_sha(path)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append({
                "benchmark_file": str(path.relative_to(root)),
                "error": str(exc)
            })

    metrics = {
        name: metric(n, d) for name, (n, d) in totals.items()
    }
    for name in metrics:
        metrics[name]["scope"] = "independently labeled benchmark examples"

    return {
        "records": records,
        "errors": errors,
        "findings": findings,
        "metrics": metrics,
        "benchmark_fingerprints": fingerprints
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--run", required=True)
    args = p.parse_args()
    root = Path(args.root).resolve()
    try:
        run = is_run(root, args.run)
        writable(run)
        result = evaluate(root)
        write_json(run / "benchmark-results.json", {
            "schema_version": 1,
            "run_id": run.name,
            "cases": result["records"],
            "skipped": result["errors"]
        })
        write_json(run / "metrics.json", {
            "schema_version": 1,
            "run_id": run.name,
            "metrics": result["metrics"],
            "benchmark_ids": sorted(result["benchmark_fingerprints"]),
            "benchmark_fingerprints": result["benchmark_fingerprints"],
            "limitations": [
                "Recorded outcome comparisons do not independently reproduce defects",
                "Null values mean no eligible labeled denominator",
                "Excluded invalid benchmarks are listed in skipped"
            ]
        })
        replace_findings(run, "benchmark", result["findings"])
        print(json.dumps({
            "run_id": run.name,
            "evaluated": len(result["records"]),
            "skipped": len(result["errors"]),
            "findings": len(result["findings"]),
            "metrics": result["metrics"]
        }, indent=2))
        return 0 if result["records"] else 1
    except (OSError, ValueError, TypeError) as exc:
        print("Benchmark evaluation failed: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
