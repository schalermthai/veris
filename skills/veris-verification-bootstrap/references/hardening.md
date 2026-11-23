# Veris Bootstrap Hardening

## Purpose
Improve the established verification setup without restarting
everything or weakening previously passing checks.

## Modes
bootstrap: initial setup and evidence.
harden: target known gaps, fix, compare, retain history.
validate: recheck in place; no application/runtime config changes.

## Prioritize
1. Unsafe access, secret exposure, or false PASS.
2. Unverified critical user journeys.
3. Broken independent result checks.
4. Runtime image drift and failed isolation/cleanup.
5. Flaky startup, readiness, and fixture reset.
6. Missing external identities and platform coverage.
7. Performance, documentation and optional optimizations.

## Severity
critical: unsafe side effects or fundamentally false verification.
high: required core flow impossible or reliably wrong.
medium: important limitation, flaky test, partial coverage.
low: documentation/diagnostic/efficiency issue.

## Before modifying
Read latest .veris report, profile and playbook.
Identify known-passing required checks.
State intended small change, rollback plan and approvals.
Do not invalidate the image used by running tests without planning.

## After modifying
Rerun changed checks and prior passing required checks.
Check fresh-start and cleanup.
Compare structured results to previous baseline.
Preserve full original report/evidence.

Do not silently overwrite .veris/reports/run-NNNN.md or
.veris/evidence/run-NNNN/results.json.

## Stop
Stop after requirements pass or when a blocker, approval need,
risk, or authorized budget prevents further safe progress.

Never force READY by dropping required checks.
