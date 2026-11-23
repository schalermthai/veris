# Veris Regression Conversion Playbook

## What to preserve

Preserve:
- Observable, agreed user behavior
- Meaningful workflow ordering
- Authorization and state transitions
- Relevant error outcomes
- Invariants and independent result checks

Do not preserve:
- Accidental retry clicks
- Temporary UI delays
- Arbitrary sleeps
- Disposable usernames or fixed IDs
- Incidental page layout or internal method names
- An agent's exploratory detours

## Conversion checklist

1. Read the story's final VERIFIED report and evidence.
2. Identify which behavior should remain stable over time.
3. Inspect existing tests to avoid duplicates.
4. Choose the smallest valuable scenario set.
5. Select deterministic/hybrid/agentic test style.
6. Implement test in existing framework.
7. Run twice from clean state and retain evidence.
8. Add behavioral and dependency metadata.
9. Validate the case and publish to catalog.

## Test style selection

Deterministic E2E:
- Preferred for stable navigation and precise assertions.
- Can be cheaper and easier to run in CI.
- Avoid brittle CSS selectors and fixed wait times.

Hybrid E2E:
- Use for flexible browser navigation or semantic checks.
- Keep fixtures, assertions, and cleanup deterministic.
- Requires a real runner capable of executing agentic steps.
- Track model/tool version when reproducibility depends on it.

Agentic E2E:
- For workflows where fixed automation is insufficient.
- More costly and potentially less repeatable.
- Must be bounded, evidence-based, and independently checked.

Never call a test hybrid if the runner cannot execute AI steps.

## Web UI example — Organization ownership transfer

SETUP:
- Create isolated test users A and B.
- Create organization X with A as owner.
- Prepare clean initial permissions.

DRIVER:
- Log in as A through the UI.
- Initiate transfer to B.
- Log out, log in as B.
- Accept the transfer through the UI.

CHECKER:
- UI shows B as owner.
- Authoritative ownership record points to B.
- A no longer has owner-only permissions.
- Repeated acceptance is handled appropriately if required.

TEARDOWN:
- Remove test organization and users in the isolated environment.

The test should exercise real UI transfer actions, not directly
write the final owner ID to the database.

## Public API example

For API-first products, an HTTP request IS the public surface.

SETUP:
- Provision test credentials and resource.

DRIVER:
- Make authenticated public API requests.

CHECKER:
- Assert response semantics and independently confirm state.

Do not require browser testing for an API-only product.

## CLI example

For a CLI-first product, the installed command IS the public surface.

DRIVER:
- Invoke the installed binary with realistic arguments.

CHECKER:
- Assert exit status, stdout/stderr, files, and other effects.

## Isolation principles

Use:
- Unique IDs per run
- Disposable fixtures
- Clear data ownership
- Explicit readiness conditions
- Bounded retries
- Teardown on failure
- Separate external test accounts when needed

If the original flow relied on an unsafe shared staging account,
redesign the test setup before publication.

## Avoid low-value tests

Avoid:
- Multiple cases that assert the same action without distinct risk
- Tests with only "element is visible" assertions when business
  state is the actual requirement
- Excessive full UI setup that can be replaced with safe fixtures
- Permanent tests based on transient implementation quirks

Preserve balance: unit tests, contracts, and integration tests
remain useful and should not automatically be deleted.

## Evidence expectations

Record:
- Source story ID, run ID, and implementation revision
- Test file and exact invocation
- Framework and execution environment
- Clean initial state
- Expected and actual behavior
- Two independent successful executions
- Logs/traces/screenshots with safe redaction
- Failures and changes made while stabilizing

## Failing conversion

If the newly written regression test exposes a real bug:
- Keep the case in draft state.
- Send findings back to the builder or Story Verifier.
- Fix and reverify behavior through the proper loop.
- Do not weaken assertions just to force a pass.
