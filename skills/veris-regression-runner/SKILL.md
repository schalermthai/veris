---
name: veris-regression-runner
description: >
  Execute regression test cases selected by veris-regression-selector,
  using the existing .veris verification profile, playbook, and
  Docker Compose shared runtime adapter. Validate source revision,
  catalog and policy identity, run approved deterministic E2E tests,
  preserve evidence and cleanup outcomes, classify failures, and
  produce structured execution reports. Supports preflight, run,
  and retest modes. Does not select tests or change application code.
---

# Veris Regression Runner

Version: 1.0.0
Compatible with Claude Code and OpenAI Codex.

## Mission

Execute the exact selected regression cases for the exact selected
source revision, using the reusable runtime created by
veris-verification-bootstrap v1.2.

Selection belongs to veris-regression-selector.
Permanent test authoring belongs to veris-regression-author.
Application fixes belong to the builder.

The runner collects execution evidence, enforces trustworthy
status reporting, and provides results for the PR gate.

## Principles

1. Exact selection: no silent case omissions or substitutions.
2. Exact revision: verify Git HEAD and complete diff identity.
3. Reuse .veris: do not build images or reinvent runtime lifecycle.
4. Disposable per-case instances in v1 for independent state.
5. Review commands: never execute an arbitrary metadata command.
6. Real execution: no fabricated test or environment results.
7. Preserve failures and retry history; never retry until green.
8. Treat failure as evidence requiring classification, not
   automatic proof that the product is broken.
9. Record every selected case as PASS, FAIL, BLOCKED, INFRA_ERROR,
   INCONCLUSIVE, FLAKY, or NOT_RUN.
10. Destroy owned instances in cleanup even after test failure.
11. Preserve evidence and report exact cleanup outcomes.
12. Fail closed on stale selector, missing test, unsafe command,
   unsupported test framework or environment drift.
13. Do not execute commands in production by default.
14. Keep reports and run IDs immutable once published.

## Modes

preflight:
  Validate selection, source, catalog, policy, runtime, and commands.
  No regression tests are executed.

run:
  Execute the entire validated selection. Default.

retest:
  Execute specified cases from a previous failure at the same
  validated revision. Preserve unexecuted cases as NOT_RUN.
  A partial retest is never a full passing regression gate.

These are natural-language skill arguments. The scripts use CLI
flags documented in README.md.

## Bundled resources

Read:
- references/execution-playbook.md
- references/failure-triage.md
- references/runner-safety.md
- assets/execution-policy.json
- assets/execution-plan.json
- assets/run-results.json
- assets/execution-report.md

Scripts:
- scripts/preflight.py
- scripts/init_execution.py
- scripts/execute_tests.py
- scripts/validate_results.py
- scripts/compare_executions.py

Resolve paths from the actual skill directory, not a hardcoded
Claude or Codex location.

## Project dependencies

Project bootstrap:
  .veris/verification-profile.yaml
  .veris/verification-playbook.md
  .veris/sandbox/sandbox.yaml
  .veris/sandbox/runtime.py

Regression catalog:
  .veris/regression/catalog.json
  .veris/regression/cases/

Selection:
  .veris/regression/selections/<change-id>/runs/<run-id>/selection.json
  .veris/regression/selection-policy.json

Runner policy:
  .veris/regression/execution-policy.json

If runner policy is absent, propose installing the bundled
execution-policy.json. Do not silently change security settings.

## Phase 0 — Read context

Read profile, playbook, latest bootstrap report, and runtime
contract. Confirm reusable runtime template is READY.

Record known environment limitations and required identities.

The existing shared runtime adapter is Docker Compose based.
Do not claim VM or managed sandbox execution support.

Do not rebuild images in this skill. Refer runtime drift or
missing tools to veris-verification-bootstrap mode=harden.

## Phase 1 — Validate selection and revision

Run:
  python3 <skill-dir>/scripts/preflight.py \
    --root . --selection <selection.json>

With Docker inspection when appropriate:
  ... --with-docker

Preflight must establish:
- selection.status = ready_for_runner
- selected IDs exist in the current catalog
- all mandatory cases included
- selection and catalog/policy digests match
- change source and diff digest match actual Git commits
- git HEAD matches selected head
- working tree is clean of relevant code changes
- no unresolved high-risk selection blocker
- available ready Docker Compose runtime
- approved framework and executable for each case
- image identity enforcement enabled
- required source files present

Stop if stale. Ask for reselect rather than silently
running an old manifest on new code.

## Phase 2 — Resolve safe commands

Never execute the raw test.command string from catalog metadata.

For v1, derive commands from registered test framework + file:
- playwright -> playwright test <file> --reporter=json
- pytest     -> pytest <file> -q

Pass commands as JSON argv arrays to the Bootstrap runtime adapter.

The executable must be on the sandbox runtime's approved
allowed_executables list.

v1 supports deterministic-e2e tests only.
Hybrid/agentic E2E require a separate reviewed execution adapter.
Block them explicitly rather than simulating execution.

Require a real executable test file in the correct container image.
The application-specific Bootstrap must make source/tests available
inside the exec_service; the bundled sample image is not sufficient.

## Phase 3 — Prepare execution

Initialize an immutable run directory:

  python3 <skill-dir>/scripts/init_execution.py \
    --root . --selection <selection.json>

Created:
  .veris/regression/executions/<change-id>/runs/<run-id>/
    execution-plan.json
    results.json
    execution-report.md
    evidence/

The plan records:
- exact selection path/hash
- revision
- catalog and policy identity
- per-case argv
- framework
- timeout and isolation
- initial NOT_RUN status

Do not overwrite previous runs.
Do not claim an initialized run means tests executed.

## Phase 4 — Execute via shared runtime

The project runtime adapter implements:
- provision
- start
- healthcheck
- execute
- collect
- destroy

Do not implement a second Docker lifecycle.

Default v1 strategy is sequential, one disposable instance per case.
Parallel execution is deliberately not implemented yet, because
Bootstrap's runtime allocator and project resource limits must first
be tested under concurrency.

Execute:
  python3 <skill-dir>/scripts/execute_tests.py \
    --root . --plan <execution-plan.json>

No image build occurs.
Each case uses its own provisioned instance and test state.
Ensure cleanup is attempted in a finally block.

For each case:
1. Provision from ready template.
2. Start the required services.
3. Verify health.
4. Execute approved test argv inside exec_service.
5. Inspect framework outcome.
6. Collect logs and stdout/stderr evidence.
7. Destroy instance and record cleanup.
8. Persist result before starting next case.

If runtime launch fails, record BLOCKED or INFRA_ERROR.
Do not invent an application FAIL.

## Phase 5 — Interpret framework results

Playwright:
- Run with JSON reporter.
- Require at least one executed test.
- Reject unexpected failures, flaky, or skipped results.
- If reporter output is missing or invalid, INCONCLUSIVE.

pytest:
- Require successful exit and confirmation tests passed.
- Zero collected tests is not PASS.
- Nonzero execution requires investigation.

Zero exit code alone does not prove a product passes.
Actual reporter evidence is required for PASS.

A failing assertion may indicate a product regression, a stale
test, a bad fixture, or a broken environment.

Preserve first failure as INCONCLUSIVE until evidence supports
a confirmed product FAIL or another classification.

## Phase 6 — Failure triage

Read references/failure-triage.md.

When a test has a nonzero outcome:
- Preserve raw stdout/stderr and framework evidence.
- Investigate assertion vs infrastructure vs test configuration.
- Avoid changing application or permanent test code.
- Record a reproduction or investigation recommendation.
- Do not rerun automatically to erase the first failure.

If needed, trigger an explicitly controlled retest.
A test failing then passing with no identified cause is FLAKY,
not a clean PASS.

The deterministic result validator accepts confirmed FAIL only
when an evidence-backed triage record exists.

## Phase 7 — Evidence and cleanup

Evidence stays in:
  .veris/regression/executions/<change-id>/runs/<run-id>/evidence/

The Bootstrap runtime may first write raw evidence into
.veris/runtime-instances/<id>/evidence/.

Copy run artifacts into the execution's private evidence directory.
These folders should be ignored by Git; unreviewed logs can contain
secrets even when the adapter itself stores no credentials.

Always attempt owned runtime destruction in finally.
Mark cleanup success or failure explicitly.
A case with failed cleanup must not be a clean PASS.

## Phase 8 — Validate results

Run:
  python3 <skill-dir>/scripts/validate_results.py \
    --root . --results <results.json>

Deterministically check:
- every selected case accounted for
- no unknown/duplicate case IDs
- selection path and hash unchanged
- application revision matches selected head
- PASS has real success attempt evidence and cleanup
- confirmed FAIL has triage details
- overall verdict is calculated from recorded cases
- zero selected/zero executed is never PASSED
- partial retest cannot be described as a full gate

Verdicts:
PASSED:
  All selected cases have actual passing evidence and clean teardown.

FAILED:
  One or more confirmed product regressions were reviewed.

BLOCKED:
  Required cases were not executable or not run.

INCONCLUSIVE:
  Test failures or uncertainty remain unresolved.

A passing run only protects registered selected behavior.

## Phase 9 — Compare execution runs

For retests:
  python3 <skill-dir>/scripts/compare_executions.py \
    <previous-results.json> <current-results.json>

Distinguish:
- fixed
- regressed
- still failing
- newly failing
- lost confirmation
- previously passing but not rerun
- changed source revision

If the builder modifies source, require new selection at that
revision before returning a complete green PR gate.

## Phase 10 — Report and handoff

Save a Markdown report using assets/execution-report.md.

If confirmed product failures:
  Hand off to builder / veris-story-verifier.

If test implementation defects:
  Recommend veris-regression-author mode=stabilize.

If environment failures:
  Recommend veris-verification-bootstrap mode=harden.

If selector stale or incomplete:
  Recommend veris-regression-selector mode=reselect.

Do not silently edit application code, regression tests,
selection policy, or bootstrap environment.

Final answer must state change/revision, selection, run ID,
all case counts, evidence, cleanup status, and next action.
