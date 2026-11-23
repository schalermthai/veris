#!/usr/bin/env python3
"""Optional TypeSafe Jev typed choice classifier.

Only sends the explicit allowlisted input file and only when both
--allow-network and --context-approved are given. No SDK required.
"""
import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.typesafe.ai/v1/systemone"
LABELS = ("direct", "indirect", "possible", "unrelated", "unknown")
RUBRIC = {
    "direct": "Changed implementation directly controls this user behavior.",
    "indirect": "Shared or downstream dependency can affect this behavior.",
    "possible": "Plausible impact, dependency not fully established.",
    "unrelated": "No credible relation given supplied context.",
    "unknown": "Insufficient context to assess impact reliably."
}


def good_array(value):
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def prepare(doc, batch, model):
    summary = doc.get("change_summary", "")
    if not isinstance(summary, str) or len(summary) > 12000:
        raise ValueError("Provide a safe change_summary <=12000 characters")
    qs = {}
    cases = []
    for index, case in enumerate(batch):
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            raise ValueError("Candidate must have a case ID")
        filtered = {"id": case["id"]}
        for field in ("behaviors", "components", "api_routes", "surfaces"):
            value = case.get(field, [])
            if not good_array(value):
                raise ValueError("Invalid candidate " + field)
            filtered[field] = value[:30]
        cases.append(filtered)
        qs["q" + str(index)] = {
            "type": "choice",
            "instructions": "Classify potential impact of the stated code change on regression case " +
                            filtered["id"] + ". If uncertain, choose unknown.",
            "criteria": RUBRIC
        }
    return {
        "model": model,
        "state": {"change_summary": summary, "cases": cases},
        "questions": qs
    }


def request_jev(payload, key):
    raw = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API, data=raw, method="POST",
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                body = res.read(2_000_000)
                return json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 529) and attempt < 2:
                time.sleep(1 + attempt * 2)
                continue
            raise RuntimeError("Jev HTTP status " + str(e.code))
    raise RuntimeError("Jev retries exhausted")


def normalize_answer(answer, case_id, model):
    classification = "unknown"
    probs = {}
    conf = None
    if isinstance(answer, dict) and answer.get("type") == "choice":
        for k, v in answer.get("probabilities", {}).items():
            if k in LABELS and isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 1:
                probs[k] = float(v)
        choice = answer.get("choice")
        if choice in LABELS and (not probs or choice in probs):
            classification = choice
        confidence = answer.get("confidence")
        if isinstance(confidence, (int, float)) and math.isfinite(confidence) and 0 <= confidence <= 1:
            conf = float(confidence)
    return {
        "id": case_id,
        "classification": classification,
        "probabilities": probs,
        "confidence": conf,
        "provider": "jev",
        "model": model,
        "reason": "Jev categorical judgment only; coding-agent rationale not supplied",
        "reviewed_by": None
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output")
    ap.add_argument("--model", default="jev-latest")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-network", action="store_true")
    ap.add_argument("--context-approved", action="store_true")
    ap.add_argument("--fixture-response")
    args = ap.parse_args()
    try:
        if args.batch_size < 1 or args.batch_size > 32:
            raise ValueError("batch-size must be 1..32")
        doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
        candidates = doc.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError("Missing candidates array")
        ids = [c.get("id") for c in candidates]
        if any(not isinstance(x, str) or not x for x in ids) or len(ids) != len(set(ids)):
            raise ValueError("Candidate IDs must be unique nonempty strings")
        batches = [candidates[i:i+args.batch_size]
                   for i in range(0, len(candidates), args.batch_size)]
        payloads = [prepare(doc, batch, args.model) for batch in batches]
        if args.dry_run:
            print(json.dumps({
                "network": False,
                "endpoint": API,
                "requests": payloads,
                "warning": "Inspect for sensitive content before network authorization"
            }, indent=2))
            return 0
        if args.fixture_response:
            responses = json.loads(Path(args.fixture_response).read_text(encoding="utf-8"))
            if isinstance(responses, dict):
                responses = [responses]
            if not isinstance(responses, list) or len(responses) != len(batches):
                raise ValueError("Fixture must provide one response per batch")
        else:
            if not (args.allow_network and args.context_approved):
                raise ValueError("Live Jev requires --allow-network AND --context-approved")
            key = os.getenv("TYPESAFE_API_KEY", "")
            if not key:
                raise ValueError("TYPESAFE_API_KEY is not set")
            responses = [request_jev(payload, key) for payload in payloads]
        assessments = []
        for batch, response in zip(batches, responses):
            answers = response.get("answers", {}) if isinstance(response, dict) else {}
            model = response.get("model", args.model) if isinstance(response, dict) else args.model
            for idx, case in enumerate(batch):
                assessments.append(normalize_answer(
                    answers.get("q" + str(idx)), case["id"], model
                ))
        result = {
            "schema_version": 1,
            "change_id": doc.get("change_id"),
            "provider": "jev",
            "assessments": assessments,
            "coverage_gaps": [],
            "note": "No exclusion is approved by this output."
        }
        rendered = json.dumps(result, indent=2) + "\n"
        if args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as handle:
                handle.write(rendered)
            print(json.dumps({"output": str(path), "count": len(assessments)}))
        else:
            print(rendered)
        return 0
    except (OSError, ValueError, TypeError, RuntimeError,
            urllib.error.URLError, json.JSONDecodeError) as e:
        print("Jev classification error: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
