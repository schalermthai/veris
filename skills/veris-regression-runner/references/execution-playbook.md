# Veris Regression Execution Playbook

## Primary lifecycle

1. Validate selected revision/catalog/policy.
2. Read Bootstrap runtime and project playbook.
3. Resolve a safe executable command for each case.
4. Plan a fresh instance for each test case.
5. Provision -> start -> healthcheck.
6. Execute real test command inside approved service.
7. Examine framework output and collect evidence.
8. Collect runtime logs when safe.
9. Destroy only the owned instance.
10. Persist and validate results.

## Bootstrap runtime interface

python3 .veris/sandbox/runtime.py --root . provision --owner PR-184
python3 .veris/sandbox/runtime.py --root . start --instance <id>
python3 .veris/sandbox/runtime.py --root . healthcheck --instance <id>
python3 .veris/sandbox/runtime.py --root . execute --instance <id> --argv-file <file>
python3 .veris/sandbox/runtime.py --root . collect --instance <id>
python3 .veris/sandbox/runtime.py --root . destroy --instance <id>

No implicit Docker image builds, pulls, or account provisioning.
Use the image validated and registered by Bootstrap.

## Test adapter rules

Playwright:
- Use one test file associated with the catalog case.
- Force JSON reporter on stdout where supported.
- Require nonzero number of executed tests.
- Reject skipped/flaky/unexpected results as clean pass.
- No --pass-with-no-tests.

pytest:
- Use one registered .py test path.
- Require exit 0 and evidence that tests were collected and passed.
- Nonzero exit requires triage.
- No bypass of actual test runner.

For CLI and mobile frameworks, implement a reviewed adapter
before claiming support. Do not pass arbitrary strings to shell.

## Isolation

One instance per case is the initial safe baseline.
Each instance has its own Docker Compose project name.

Verify database volumes and external service identities are not
shared in ways that invalidate independence.

Clean state and reliable teardown are mandatory.
Serial execution avoids concurrency assumptions in v1.

## Revision fidelity

The selection records exact Git base/head and diff digest.
The runner recomputes that commit-to-commit diff.
The local HEAD must match selected head.

Untracked application files and tracked changes invalidate the
reproducible snapshot. Artifacts under known .veris execution
directories may be excluded from the cleanliness check.

## Evidence

Record:
- instance ID and environment identity
- launch and test command metadata
- start and finish times
- exit code and actual runner output
- artifacts in evidence/<case-id>
- teardown status and errors
- failure categorization

Raw logs may contain credentials. Restrict permissions and do not
commit them without redaction.

## CI gate

PASSED only when every selected case really passed with clean cleanup.
FAILED only when a product regression has supporting triage.
BLOCKED when essential cases could not execute.
INCONCLUSIVE when tests failed but their meaning is unresolved.

A zero-case manifest does not establish a passing regression gate.
