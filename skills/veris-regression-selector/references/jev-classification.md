# Veris — Jev Semantic Classification

## Vendor contract

Official TypeSafe API:
  POST https://api.typesafe.ai/v1/systemone
  Authorization: Bearer TYPESAFE_API_KEY
  Content-Type: application/json

Request:
  model: jev-latest or an authorized versioned model
  state: string/object/array
  questions: map of typed question IDs

We use type=choice with criteria:
  direct, indirect, possible, unrelated, unknown

Response:
  answers[question_id].choice
  answers[question_id].probabilities
  answers[question_id].confidence
  model and usage

Official docs:
  https://docs.typesafe.ai/api/system-one
  https://docs.typesafe.ai/introduction/quickstart

## Design

A Jev batch evaluates multiple candidate regression cases against
a shared sanitized change summary.

Batch size defaults to eight for bounded requests; this is a Veris
configuration choice, NOT a stated API hard limit.

Input file example:
{
  "change_id": "PR-184",
  "change_summary": "PermissionService authorization logic changed",
  "candidates": [
    {
      "id": "org-transfer-ownership",
      "behaviors": ["organization.transfer"],
      "components": ["PermissionService"],
      "api_routes": ["/organizations/:id/transfer"]
    }
  ]
}

Do not put raw secrets, customer data, full proprietary source,
or authentication tokens into change_summary.

## Safe invocation

Preview:
  python3 scripts/classify_with_jev.py --input safe.json --dry-run

After explicit permission to send the reviewed payload:
  python3 scripts/classify_with_jev.py --input safe.json \
    --output impact.json --allow-network --context-approved

Requires TYPESAFE_API_KEY from the process environment.
Never log or serialize credentials.

## Output

{
  "schema_version": 1,
  "change_id": "PR-184",
  "provider": "jev",
  "model": "jev-1.14.0",
  "assessments": [
    {
      "id": "org-transfer-ownership",
      "classification": "indirect",
      "probabilities": {"indirect": 0.78},
      "confidence": 0.78,
      "reason": "Jev label only; independent reasoning pending",
      "reviewed_by": null
    }
  ]
}

This shape is illustrative. The model field comes from API response.

## Boundaries

Jev is a classifier, not a dependency analyzer or test runner.
Its returned confidence does not prove impact or lack of impact.

The coding agent should:
- Inspect direct and indirect dependency evidence.
- Add a human-readable reason grounded in available context.
- Independently review any proposed unrelated classification.
- Leave reviewed_by null unless that review actually occurred.

Conservative fallback:
- Missing key -> coding-agent review or unknown/include.
- API failure -> coding-agent review or unknown/include.
- Malformed response -> unknown/include.
- Low-confidence unrelated -> unknown/include.
- Jev unrelated without review -> include.

Do not calibrate a hard exclusion threshold without historical
PRs and known regression cases.
