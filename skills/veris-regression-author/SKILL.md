---
name: veris-regression-author
description: >
  Convert successfully verified story workflows into permanent,
  repeatable E2E regression tests. Use when veris-story-verifier has
  produced a VERIFIED final story run and behavior must be protected
  against future changes. Read the project's .veris profile and
  playbook, implement tests using existing testing frameworks,
  run and stabilize them, create test metadata, and publish ready
  tests into the Veris regression catalog. Not for ad hoc story QA,
  selecting regression suites, or running unrelated test suites.
---

# Veris Regression Author

Version: 1.0.0
Compatible with Claude Code and OpenAI Codex.

## Mission

Turn verified story behavior into automated, repeatable regression
coverage. Preserve the user-facing behavior, not a brittle recording
of every action the QA agent happened to take.

The authoritative sources are:
- Current story acceptance criteria
- A successful final Veris Story Verifier result
- Recorded verification evidence
- The existing project playbook and verification profile
- The application's actual supported testing frameworks

The result is:
1. A real executable E2E test in the application's test directory.
2. A test case metadata record with provenance and dependencies.
3. Execution evidence and a human-readable conversion report.
4. A regression catalog entry for later test selection.

Do not publish a draft or unexecuted test as READY.

## Activation

Use after a story has passed veris-story-verifier.
Possible invocations:
- Convert verified STORY-142 to regression coverage.
- Author regression tests for the successful ownership-transfer flow.
- Stabilize and publish a previously drafted regression case.

Default mode: author.
Modes:
- author: design and implement tests from verified story evidence.
- stabilize: improve an existing draft and rerun repeatability checks.
- publish: validate and register a completed case without rewriting it.

Arguments are natural-language skill instructions, not a shell API.

## Principles

1. Source-gated: only completed VERIFIED final story runs qualify.
2. Reuse .veris: do not recreate the bootstrap environment.
3. Behavior first: tests describe lasting business behavior.
4. Real surface: driver actions use the interface users experience.
5. Deterministic first: prefer explicit fixtures and assertions.
6. Hybrid when justified: agentic actions are optional, bounded,
   auditable, and only used with a runner capable of executing them.
7. Independent oracle: a click or success toast alone is insufficient
   when the expected result includes persistence or permissions.
8. Isolation: test data, credentials, and external effects must be safe.
9. Reproducible: reset the environment and run the test repeatedly.
10. Provenance: record source story, run, criteria, scenario, revision.
11. No fake readiness: metadata alone does not prove test execution.
12. Extend existing infrastructure; avoid introducing unnecessary
    test libraries, CI systems, or duplicate frameworks.
13. Preserve existing unit and integration coverage.
14. Report unsupported paths and incomplete automation honestly.

## Bundled files

Read as needed:
- references/conversion-playbook.md
- references/catalog-contract.md
- assets/regression-plan.md
- assets/regression-report.md
- assets/case-metadata.json

Scripts:
- scripts/inspect_story.py
- scripts/scaffold_case.py
- scripts/validate_case.py
- scripts/publish_catalog.py

All scripts use Python 3.9+ standard library only.
Resolve paths relative to the skill's actual installation.

## Phase 0 — Inspect project and verified story

Read:
- .veris/verification-profile.yaml
- .veris/verification-playbook.md
- .veris/bootstrap-report.md when available
- Story final run results.json
- Story verification-report.md and relevant evidence
- Existing E2E test framework and CI configuration

Use:
  python3 <skill-dir>/scripts/inspect_story.py \
    --root . \
    --source .veris/stories/STORY-142/runs/run-0002/results.json

The source gate requires:
- mode = final
- overall_verdict = verified
- recorded implementation revision
- meaningful required acceptance criteria
- all required scenarios passed
- successful independent checks and existing evidence
- no open blocking defects
- valid scenario-to-criterion coverage

A story with only targeted or partial verification does not qualify.

The source checker validates records and evidence existence;
it cannot prove those artifacts truthfully represent execution.
Inspect the human report and actual evidence as well.

If blocked, return to veris-story-verifier. Never bypass the gate
by manually editing the source verdict.

## Phase 1 — Select lasting regression behaviors

Identify the smallest valuable set of user journeys that protects
the story's confirmed behavior.

For each candidate consider:
- Business criticality
- Realistic future regression risk
- Distinct behavior, not duplicate steps
- Authorization and persistent state changes
- Cross-surface or cross-service behavior
- Known incident classes
- Maintenance and execution cost

One story may yield several tests. Multiple acceptance criteria
may be covered by one test if the workflow is coherent.

Do not convert every exploratory click into a separate regression.
Do not encode temporary implementation quirks as the contract.

Read references/conversion-playbook.md.

## Phase 2 — Decide test style and integration

Inspect existing test frameworks and repository patterns.

Prefer:
- Existing Playwright suite for web applications
- Existing API/contract harness for public API applications
- Existing CLI integration test harness for CLI applications
- Existing emulator/device E2E harness for native mobile applications

Choose test style:
- deterministic-e2e: fixed interactions and precise assertions
- hybrid-e2e: fixed steps plus bounded agentic navigation/assertion
- agentic-e2e: mostly agent-driven when deterministic steps cannot
  reliably express the intended workflow

A hybrid test is only runnable when the project's test runner
actually supports the agentic steps. Do not invent framework APIs.

Favor deterministic setup, assertions, and cleanup even when driver
navigation is agentic. Do not choose agentic testing merely because
the original Story Verifier was agentic.

Document tradeoffs and residual limitations.

## Phase 3 — Scaffold regression case metadata

For each chosen passing scenario, create an initial metadata record:

  python3 <skill-dir>/scripts/scaffold_case.py \
    --root . \
    --source .veris/stories/STORY-142/runs/run-0002/results.json \
    --scenario S-01 \
    --case org-transfer-ownership \
    --suite organizations

Generated files:
- .veris/regression/cases/org-transfer-ownership.json
- .veris/regression/plans/org-transfer-ownership.md

Do not overwrite existing case metadata silently.
Inspect existing cases before creating overlapping coverage.

Populate metadata:
- behaviors protected
- user-facing surfaces
- affected components and public API routes
- risk level and labels
- executable test file and test name
- framework and command
- setup, surface actions, independent assertions, and cleanup

Metadata should describe actual test behavior, not speculative
dependencies. Mark uncertain dependency relationships in the report.

## Phase 4 — Implement the executable E2E test

Write the actual test in the repository's established suite,
such as tests/e2e/ or e2e/. Use the documented test harness.

Setup:
- Create isolated accounts and fixtures.
- Prepare required initial state.
- Use predictable data and cleanup.

Driver:
- Exercise the public surface.
- Perform the meaningful user actions.
- Use stable locators or semantic UI interactions when possible.
- Do not bypass the UI/API/CLI behavior under test.

Checker:
- Assert the user-visible outcome.
- Assert relevant persisted results and permissions independently.
- Cover important negative outcomes where justified.

Cleanup:
- Reset state and release resources, even after failure.

Prevent:
- Arbitrary sleeps instead of readiness conditions
- Shared mutable fixture data
- Reliance on external production identities
- Weak assertions that only check a success toast
- Recording-generated noise
- Permanent tests of accidental implementation details

Do not disable, delete, or replace unit tests automatically.

## Phase 5 — Execute and stabilize

Run the exact new test using the project's real test runner.

Record command, implementation revision, exit code,
environment, evidence files, and observations.

A case is considered stable only after at least two separate
successful runs from clean initial state, unless an explicit
project policy defines a stricter threshold.

Record each run with a distinct run ID. Preserve failed attempts
as evidence. Do not hide initial failures behind later successes.

If failures appear:
- Distinguish product defect from test flakiness.
- Repair the test when its assumptions or selectors are wrong.
- Return to the builder/story verifier when the product fails.
- Rerun from clean state and maintain failure history.

Do not mark a test ready if the required runner, browser, device,
or external identity is unavailable.

## Phase 6 — Validate metadata and execution evidence

Complete the case JSON according to:
- assets/case-metadata.json
- references/catalog-contract.md

Before publishing, set status = ready only when:
- Source Story Verifier result remains valid.
- Executable test exists in the repository.
- Behavior, surface steps, and assertions are recorded.
- Framework and actual invocation command are known.
- Teardown is documented.
- At least two distinct clean-state passing executions exist.
- Each pass has a zero exit code and existing evidence.
- No open blocking issue remains.

Run:
  python3 <skill-dir>/scripts/validate_case.py \
    --root . \
    --case .veris/regression/cases/org-transfer-ownership.json

The validator checks structure, provenance, and evidence references.
It cannot independently attest that commands truly ran or that the
test's assertions are semantically sufficient. The author must
inspect the executable code and observed results.

## Phase 7 — Publish catalog entry

Only publish valid ready cases.

Run:
  python3 <skill-dir>/scripts/publish_catalog.py \
    --root . \
    --case .veris/regression/cases/org-transfer-ownership.json

This updates:
  .veris/regression/catalog.json

Catalog fields include:
- stable case ID and suite
- test path, framework, and kind
- risk and behavioral tags
- affected components/routes
- source story and revision
- last validated run

Never publish an incomplete draft as runnable coverage.
Never silently overwrite an existing case ID or alias another test.

On subsequent revisions of a case, validate the update and use an
explicit approved replacement workflow.

## Phase 8 — Report and handoff

Produce a case conversion report using:
  assets/regression-report.md

Store it under:
  .veris/regression/reports/<case-id>.md

Include:
- Source verification provenance
- Behavior being protected
- Test strategy and why it was selected
- Exact executable test path and command
- Setup, Driver, Checker design
- Execution history and evidence
- Known limitations and residual flakiness
- Catalog publication result
- Relevant dependencies/tags for future selection

If test creation was incomplete, keep status draft.
Document blockers and the next stabilization action.

Handoff:
- veris-regression-selector reads the catalog to select relevant cases.
- veris-regression-runner executes chosen tests.
- veris-verification-auditor can challenge the coverage later.

Do not perform impact selection for unrelated PRs in this skill.
