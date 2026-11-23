# Veris Regression Catalog Contract v1

## Purpose

Provide reliable, machine-readable metadata for regression
selection without coupling selection to a specific test framework.

Catalog:
  .veris/regression/catalog.json

Case metadata:
  .veris/regression/cases/<case-id>.json

Project executable tests:
  Whatever directory/framework the repository already uses.

## Required catalog schema

{
  "schema_version": 1,
  "cases": [
    {
      "id": "org-transfer-ownership",
      "suite": "organizations",
      "metadata_path": ".veris/regression/cases/org-transfer-ownership.json",
      "test_file": "tests/e2e/org-transfer.spec.ts",
      "framework": "playwright",
      "kind": "deterministic-e2e",
      "risk": "high",
      "behaviors": ["organization.transfer", "organization.permissions"],
      "surfaces": ["web"],
      "components": ["OrganizationService", "PermissionService"],
      "api_routes": ["/organizations/:id/transfer"],
      "tags": ["ownership", "authorization"],
      "source_story": "STORY-142",
      "source_revision": "abc123",
      "latest_run_id": "local-pass-2"
    }
  ]
}

These field names are the v1 contract intended for
veris-regression-selector and veris-regression-runner.

## Case metadata contract

Top-level:
- schema_version = 1
- id = unique stable slug
- title = human-readable behavior name
- status = draft | ready
- source = original story verification provenance
- coverage = suite, risk, behaviors, surfaces, dependencies, tags
- test = executable path, framework, command, kind, assertions
- execution = list of execution records
- maintenance = ownership and notes

The source must reference an existing final VERIFIED Story Verifier run.
The selected scenario must be PASS with valid evidence.

## Coverage metadata

suite:
  A stable logical functional suite, e.g. organizations.

risk:
  critical | high | medium | low

behaviors:
  Stable business-level identifiers, e.g. organization.transfer.

surfaces:
  The real product surface, e.g. web or public-api.

components:
  Known implementation dependencies useful for diff impact analysis.

api_routes:
  Known public routes associated with the protected behavior.

tags:
  Extra labels for selection, such as auth or cross-browser.

Avoid inventing component dependencies to make a test look useful.
Unknown fields may be empty; document why in the author report.

## Execution records

Each execution entry should contain:
- id: stable unique run identifier
- status: pass | fail | blocked
- revision: source code revision tested
- command: actual command executed
- exit_code: actual exit code, if available
- clean_state: true only for isolated, reset starting state
- evidence: list of relative paths within project

At least two independent successful clean-state runs
are required for status=ready in this skill version.

Metadata validation checks only file existence and record
consistency. It cannot attest actual execution authenticity.

## Why two levels?

Case files hold detailed provenance and implementation details.
Catalog contains a compact index needed by selector.

Do not let the selector rewrite case metadata.
Do not let the runner silently rewrite source provenance.
Future Veris skills may create separate execution reports.

## Updating catalog

Only ready cases may be added.

The publisher prevents accidental duplicate IDs.
Existing entries must not be silently replaced.
Changes to registered cases require explicit review and
validation of the new executable test.
