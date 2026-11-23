# Veris Verification Technique Selection

Choose a technique by user-facing surface, observability,
repeatability, isolation, cost, and risks left uncovered.

## Web application
Primary: browser-driven E2E (e.g. Playwright).
Supporting: database assertions, traces, screenshots,
accessibility, cross-browser checks when relevant.
Never replace the required UI action with an internal API shortcut.

## Public API
Primary: authenticated public endpoint workflow.
Supporting: contract, state, authorization, retries,
idempotency, side-effect checks.

## CLI
Primary: installed CLI binary with realistic input.
Supporting: exit code, output, filesystem, persisted state,
interactive sessions and error paths.

## Mobile
Primary: emulator/simulator or authorized test device UI.
Supporting: logs, local state, backend checks, permissions,
network interruption, backgrounding, supported OS versions.

## External integration
Primary: real authorized test account or provider sandbox mode.
Supporting: webhook delivery, permission lifecycle, retries,
external state and failure handling.
Mock-only tests are not proof of full external E2E.
Secrets must be provided securely at runtime.

## Asynchronous workflow
Trigger via public interface, observe completion conditions.
Check queue/event state and persistent results as needed.
Avoid fixed sleeps as the only synchronization.

## Complementary techniques
- Unit: focused deterministic logic
- Integration: dependencies and service boundaries
- Contract: API and message compatibility
- Property-based: invariant checking
- Differential: compare known-good behavior
- Exploratory: unexpected interactions and UX defects
- Fuzzing: unusual inputs and action sequences
- Accessibility: semantics, keyboard, focus and contrast
- Load testing: capacity/latency with bounded approved resources

## Technique recommendation record
Technique:
Surface:
Why:
Failure modes:
Dependencies:
Test identities:
Isolation:
Evidence:
Cost:
Limitations:
Priority: required | recommended | optional
Status: proven | proposed | unavailable

Preserve existing useful tests. Do not blindly delete unit tests.
