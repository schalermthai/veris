# Veris Regression Author v1.0

Skill 03 in the Veris verification lifecycle.

Convert a VERIFIED final Story Verifier run into durable E2E tests
and a machine-readable regression catalog.

## Installation

Claude Code:
  .claude/skills/veris-regression-author/

Codex:
  .agents/skills/veris-regression-author/

Install the whole folder, including scripts and references.
One canonical copy may be linked into both directories.

## Invocation

Claude Code:
  /veris-regression-author mode=author
  Convert verified STORY-142 to reusable E2E regression tests.

Codex:
  $veris-regression-author mode=author
  Convert verified STORY-142 to reusable E2E regression tests.

Modes:
- author
- stabilize
- publish

## Inputs

- .veris/verification-profile.yaml
- .veris/verification-playbook.md
- .veris/stories/<story>/runs/<run>/results.json
- Story report and actual evidence
- Existing test framework and test code conventions

## Scripts

Check source:
  python3 scripts/inspect_story.py --root . --source \
    .veris/stories/STORY-142/runs/run-0002/results.json

Create draft:
  python3 scripts/scaffold_case.py --root . --source \
    .veris/stories/STORY-142/runs/run-0002/results.json \
    --scenario S-01 --case org-transfer-ownership \
    --suite organizations

Validate completed case:
  python3 scripts/validate_case.py --root . --case \
    .veris/regression/cases/org-transfer-ownership.json

Publish:
  python3 scripts/publish_catalog.py --root . --case \
    .veris/regression/cases/org-transfer-ownership.json

All scripts are standard-library Python 3.9+.
They manage provenance, metadata, and publication.
They do not fabricate or execute project-specific E2E tests.

## Outputs

Project executable test:
  e2e/<existing-project-test-convention>

Veris metadata:
  .veris/regression/cases/<case-id>.json
  .veris/regression/plans/<case-id>.md
  .veris/regression/reports/<case-id>.md
  .veris/regression/evidence/<case-id>/
  .veris/regression/catalog.json

## Test readiness

A ready case has:
- verified final story source
- correct source criteria and scenario IDs
- actual executable test file
- meaningful public-surface steps
- independent assertions and cleanup
- real test command
- at least two independent clean-state passing runs
- actual evidence files

Drafts are not published as runnable regression coverage.

## Tests

From this skill's root:
  python3 -m unittest discover -s tests -v

## Example

Story: ownership transfer
Source scenario: S-01
Case: org-transfer-ownership
Suite: organizations

The agent might implement an existing Playwright test in
tests/e2e/organization-transfer.spec.ts, verify that transfer works,
check persisted ownership/authorization, run it repeatedly, and then
publish its metadata.

The skill does NOT prescribe Playwright to all projects.

## Next skills

veris-regression-selector:
  Chooses tests from .veris/regression/catalog.json based on PR impact.

veris-regression-runner:
  Executes tests and produces regression execution reports.

Important: Generating metadata is not the same as successfully
executing a regression test. Verify both the code and evidence.
