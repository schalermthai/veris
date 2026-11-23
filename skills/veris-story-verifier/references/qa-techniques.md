# Veris Story QA Technique Playbook

## Goal

Verify acceptance criteria, then explore nearby risk in a bounded way.

## Positive paths

Exercise the normal user journey through its real public surface.
Confirm final visible state and the authoritative state when relevant.

## Negative paths

Check relevant unauthorized, invalid, duplicate, missing,
expired, or unavailable-service behavior.

Do not add arbitrary requirements not supported by the story.

## State transitions

For workflows with states, test:
- starting state
- intended transitions
- disallowed transitions where relevant
- resulting state
- persisted state and side effects

## Multi-user and authorization

Use separate disposable accounts.
Switch identity through the real interface when necessary.
Verify both gaining and losing permissions.
Check backend authorization independently when appropriate.

## Boundary and repeat-action checks

Consider:
- empty, long, or malformed inputs
- double submit
- cancel and reopen
- refresh, back, retry
- stale sessions and expired links
- relevant concurrency or idempotency

## UI exploration

Observe console and network errors, unexpected dialogs,
broken states, focus behavior, confusing messaging, and
accessibility problems. Keep investigation risk-based.

## Browser and device variance

Use the surfaces and engines supported by the .veris profile.
Do not claim WebKit/Safari compatibility after Chromium-only
testing, or mobile UI correctness from API tests.

## Third-party integrations

Prefer provider test identities and isolated workspaces.
Distinguish mocked integration checks from real end-to-end
integration behavior. Use least privilege and protect secrets.

## Supporting checks

Unit tests: precise code behavior.
Integration tests: service and dependency boundaries.
Contract tests: external compatibility.
Property tests: invariants over inputs.
Differential tests: compare against known-good behavior.
Browser E2E: actual UI workflow.
Manual-like exploratory agents: unanticipated defects.

Supporting checks should not be mislabeled as real-surface E2E.

## Defect classification

Acceptance failure: expected story behavior failed.
Unexpected defect: nearby or UX problem outside explicit criteria.
Environment issue: verification prerequisites unavailable.
Inconclusive: test ran but evidence cannot establish outcome.

Severity:
critical: major unsafe failure or essential system damage.
high: broken core journey, authorization, or important data issue.
medium: significant secondary behavior or UX defect.
low: small impact and minor inconsistencies.

## Evidence standard

Record initial state, actual actions, expected/actual outcome,
independent checks, tool/environment, implementation revision,
and supporting screenshot/log/trace/video where relevant.

Retries must be recorded, not silently filtered out.

## Targeted vs final

targeted: run only currently testable slices, retain unfinished
criteria as not_run. Do not declare a whole unfinished story verified.

retest: check original defects and changed nearby behavior,
compare with previous run, distinguish omissions from regressions.

final: map every required criterion to actually executed tests.
