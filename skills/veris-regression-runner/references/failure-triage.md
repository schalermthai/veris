# Veris Failure Triage

## Do not equate failed command with product regression

A test can fail because:
- application behavior is actually broken
- selectors or fixture data are stale
- environment or external services are unavailable
- runner config is incorrect
- execution is flaky
- evidence is incomplete

## Classification

PASS:
  Valid runner execution, positive framework result, no skipped/flaky
  tests in required case, evidence exists and cleanup succeeded.

FAIL:
  Confirmed application regression with explicit triage record and
  evidence, not merely a nonzero shell exit.

INFRA_ERROR:
  A test environment or lifecycle operation malfunctioned.

BLOCKED:
  Missing prerequisite prevented meaningful execution.

INCONCLUSIVE:
  Test attempted, but no reliable verdict can yet be established.

FLAKY:
  Comparable attempts disagree without a known causal fix.

NOT_RUN:
  Selected case was never attempted.

## Recommended investigation

1. Preserve the first failure.
2. Check source revision and runtime state.
3. Inspect framework-level output and console errors.
4. Determine whether a real assertion failed.
5. Check fixture setup, account permissions, and readiness.
6. Reproduce in a clean controlled environment if needed.
7. Inspect independent state and UI behavior.
8. Record a justified classification and evidence.
9. Send product bugs to builder and test bugs to Regression Author.

## Triage record

{
  "confirmed": true,
  "category": "product_regression",
  "reviewed_by": "coding-agent",
  "reason": "Observed ownership permission persists after transfer",
  "evidence": ["evidence/org-transfer/stderr.txt"]
}

Confirmation is a recorded review, not an automated claim of truth.
A deterministic validator checks record shape and evidence existence,
not whether the diagnosis is correct.

## Retesting

A fresh attempt is a new recorded execution.
Do not erase or replace an original failing attempt.
Fail-then-pass without identified cause => FLAKY.

A targeted retest is NOT a full regression pass.
When source changes, reselect against the new revision.
