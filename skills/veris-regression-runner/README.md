# Veris Regression Runner v1.0

Skill 05 in the Veris verification lifecycle.

Supports Claude Code and OpenAI Codex using the same SKILL.md
and Python standard-library helper scripts.

## Install

Claude Code:
  .claude/skills/veris-regression-runner/

Codex:
  .agents/skills/veris-regression-runner/

## Requirements

- Python 3.9+
- Git
- Docker Compose v2 + a working Docker daemon
- Bootstrap v1.2 runtime at .veris/sandbox/runtime.py
- Bootstrap sandbox template configured for the actual application
- .veris/regression/catalog.json from Skill 03
- Valid selection.json from Skill 04
- Project-installed Playwright or pytest in the runtime's exec service

The Bootstrap v1.2 example container is NOT application-ready.
You must harden it for your application first.

## Modes

preflight:
  /veris-regression-runner mode=preflight

run:
  /veris-regression-runner mode=run

retest:
  /veris-regression-runner mode=retest

For Codex replace /veris... with $veris...

## Install project execution policy

Copy assets/execution-policy.json into:
  .veris/regression/execution-policy.json

Review limits and approved frameworks.

## Usage

Preflight:
  python3 scripts/preflight.py --root . \
    --selection .veris/regression/selections/PR-184/runs/run-0001/selection.json

With Docker inspection:
  python3 scripts/preflight.py --root . --with-docker \
    --selection <selection.json>

Create execution run:
  python3 scripts/init_execution.py --root . \
    --selection <selection.json>

The command prints the actual run directory and plan path.

Run selected cases:
  python3 scripts/execute_tests.py --root . \
    --plan <printed-plan-path>

Validate:
  python3 scripts/validate_results.py --root . \
    --results <printed-results-path>

Compare:
  python3 scripts/compare_executions.py \
    <previous-results.json> <current-results.json>

For a partial retest, execute_tests.py supports --case <case-id>.
Unselected test cases remain NOT_RUN and the run cannot pass as
a complete regression gate.

## Supported test adapters

playwright deterministic-e2e:
  ["playwright", "test", "<test-file>", "--reporter=json"]

pytest deterministic-e2e:
  ["pytest", "<test-file>", "-q"]

These are run INSIDE the configured Bootstrap runtime.
Your runtime.allowed_executables must explicitly permit
"playwright" or "pytest" as required.

Hybrid and agentic test kinds are blocked until an explicitly
reviewed project-specific runner adapter is available.
Raw test.command metadata is NEVER executed directly.

## Execution strategy

v1 is serial: one fresh disposable runtime instance per case.

This avoids state collisions and keeps the first implementation
auditable. Parallel execution can follow after the shared
runtime allocator is validated under concurrency.

## Failure classification

Successful exit and valid framework report: PASS.
Failed test execution: INCONCLUSIVE until triaged.
Confirmed product regression: FAIL with a triage record.
Infrastructure unavailable: BLOCKED / INFRA_ERROR.
Unexplained fail-then-pass: FLAKY.
Not executed: NOT_RUN.

A failed test does not automatically prove broken product code.

## Output

.veris/regression/executions/<change-id>/runs/<run-id>/
  execution-plan.json
  results.json
  execution-report.md
  evidence/

The execution directory and raw logs should not be committed to
source control without review. The initializer creates a local
.gitignore for run evidence.

## Safety

No raw catalog command execution, no shell=True, no implicit image
builds, no production access without explicit authorization.

A clean worktree and exact Git head/diff are required by default.
The image identity must be enforced in sandbox.yaml for CI use.

The runtime adapter should be invoked only on a trusted, authorized
Docker host. Docker project naming does not protect against hostile
containers.

## Test helper scripts

From skill root:
  python3 -m unittest discover -s tests -v

The unit tests are offline and do not need Docker.
A full integration test requires a real project and configured runtime.

## Downstream

veris-verification-auditor consumes execution history and can
evaluate missed regressions, false verdicts, and flaky coverage.
