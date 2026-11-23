---
name: veris-verification-bootstrap
description: >
  Bootstrap, harden, or validate a project's agent-driven verification
  environment and reusable runtime. Discover application surfaces and
  dependencies, recommend verification techniques, generate a project
  playbook, create Docker Compose sandbox definitions, validate image
  identity and runtime lifecycle, and preserve evidence-backed reports.
  Use for new projects, infrastructure drift, and verification hardening.
  Not for routine story QA or PR regression execution.
---

# Veris Verification Bootstrap

Version: 1.2.0
Compatible with Claude Code and OpenAI Codex.

## Mission

Establish and improve the verified environment in which independent
AI agents can test real application behavior.

Own reusable environment DEFINITIONS and validated image references.
Do not own temporary test instances used by Story Verifier or Runner.

Never claim a working environment based on writing configuration
files alone.

## Modes

bootstrap: Initial project discovery and verified setup.
harden: Read prior gaps, make targeted changes, and revalidate.
validate: Re-execute checks without changing application or runtime
          configuration; write fresh report/evidence only.

Default bootstrap if no profile exists; otherwise validate.
Use harden when the user requests a fix or known gaps need repair.
These modes are natural language skill parameters.

## Principles

1. Surface fidelity: use the same interface as a real user.
2. Independent oracles: confirm important outcomes beyond a toast.
3. Discovery before tool selection: reuse existing reliable systems.
4. Setup / Driver / Checker responsibilities must be explicit.
5. Deterministic fixtures, readiness checks, assertions, cleanup.
6. Isolated, disposable environments and test identities by default.
7. No production access, cloud provisioning, or spending without approval.
8. Secrets never appear in skills, repository config, or reports.
9. Store only reproducible facts; distinguish proposal from evidence.
10. Preserve reports and previous passing checks across hardening.
11. Runtime images and running instances are different assets.
12. Runtime execution must use reviewed adapters and bounded resources.
13. Avoid silently modifying established project instructions.
14. Unsupported VM/cloud providers must fail closed, not be simulated.

## Read bundled resources

- references/techniques.md
- references/hardening.md
- references/runtime-contract.md
- assets/verification-profile.yaml
- assets/verification-playbook.md
- assets/bootstrap-report.md
- assets/run-results.json
- scripts/inventory.py
- scripts/compare_runs.py
- scripts/scaffold_runtime.py
- scripts/runtime_adapter.py

Resolve paths relative to this skill's directory.

## Phase 0 — Inspect history and determine scope

Read existing:
- .veris/verification-profile.yaml
- .veris/verification-playbook.md
- .veris/bootstrap-report.md
- .veris/reports/ and relevant evidence
- .veris/sandbox/sandbox.yaml if present

In harden mode, identify specific previously reported gaps,
prior passing checks, and what should change. Do not restart
the entire bootstrap unnecessarily.

In validate mode, preserve application and runtime definitions.

## Phase 1 — Discover project requirements

Inspect:
- Repository architecture, runtime, entrypoints
- User-facing web, API, CLI, mobile, integration surfaces
- Existing builds, tests, CI, dependencies, services
- Startup commands, health checks, fixture shortcuts
- Databases, caches, queues, background workers
- Authentication, external test identities, permissions
- Browser/device support and critical user workflows
- Current Docker, devcontainer, VM or sandbox infrastructure
- Existing evidence and production failure lessons

Optional:
  python3 <skill-dir>/scripts/inventory.py --root .

Label findings observed, inferred, or unknown.
Never read or disclose secret values unnecessarily.

## Phase 2 — Recommend verification techniques

Read references/techniques.md.

For each important public surface recommend:
- Primary end-to-end technique
- Supporting deterministic assertions
- Isolation and fixtures
- Tools and test identities
- Evidence and limits
- Why this technique is appropriate

Evaluate but do not indiscriminately add:
unit, integration, contract, property, differential, browser E2E,
agentic exploratory, fuzzing, accessibility, cross-browser, load.

Classify required/recommended/optional and proven/proposed/unavailable.

## Phase 3 — Design reusable runtime

Read references/runtime-contract.md.

Define:
- Provider and isolation method
- Image build and immutable identity strategy
- Runtime dependencies and required services
- Environment variables by name; runtime secret injection
- Setup/start/healthcheck/execute/collect/destroy lifecycle
- Resource, runtime, concurrency and cost limits
- Data reset and cleanup
- Boundaries around host mounts, networks and external volumes

For Docker Compose projects, optionally scaffold:

  python3 <skill-dir>/scripts/scaffold_runtime.py --root .

This creates:
- .veris/sandbox/sandbox.yaml
- .veris/sandbox/compose.yaml
- .veris/sandbox/Dockerfile
- .veris/sandbox/runtime.py
- .veris/runtime-instances/.gitignore

The generated Docker sample is ONLY a demonstration. It does NOT
represent the user's application until customized and verified.
The sandbox template defaults to status=draft and cannot provision.

Do not overwrite an existing sandbox configuration or runtime adapter.
Harden changes must be reviewed, precise and reversible.

Other providers can use the same conceptual lifecycle, but the
provided executable adapter supports Docker Compose ONLY.

## Phase 4 — Review, build and validate image

Before any build or provisioning:
- Review the Dockerfile and build context.
- Inspect for secrets in the image context.
- Verify permitted external resource access.
- Check Compose services, volumes, host networking and privileges.
- Confirm spending and infrastructure approval.

Offline check:
  python3 .veris/sandbox/runtime.py --root . validate

If Docker is installed, inspect rendered Compose configuration:
  python3 .veris/sandbox/runtime.py --root . validate --with-docker

Building is an explicit approved action:
  python3 .veris/sandbox/runtime.py --root . build --approved

Record image identity for each required service:
- Registry image with immutable digest when available
- Or locally built Docker image ID for host-local validation

Avoid treating a floating tag as immutable evidence.
For portable CI, prefer registry-pinned image digests.

Only set sandbox template_status=ready after:
- The image and required services are genuinely built/available
- Configuration was reviewed and validated
- A real representative user workflow was run
- The documented environment is reproducible
- Isolation and teardown succeeded
- Existing baseline checks remain passing

Do NOT set template_status=ready for the bundled demonstration alone.

## Phase 5 — Discover a representative flow

Choose a small vertical-slice real user journey.

Example:
create disposable account -> log in -> create domain item ->
confirm UI outcome -> independently check persistent state.

SETUP:
- Start isolated dependencies and prepare controlled test data.

DRIVER:
- Use the browser, public API, installed CLI or actual mobile UI.
- Do not replace the user action with hidden internal state mutations.

CHECKER:
- Independently evaluate the expected result.
- Inspect side effects and anomalous behavior.
- Preserve evidence.

If blocked, report the missing resource instead of pretending success.

## Phase 6 — Prove reusable runtime lifecycle

For a customized, approved READY Docker template:

  python3 .veris/sandbox/runtime.py --root . provision --owner bootstrap
  python3 .veris/sandbox/runtime.py --root . start --instance <id>
  python3 .veris/sandbox/runtime.py --root . healthcheck --instance <id>
  python3 .veris/sandbox/runtime.py --root . execute --instance <id> --argv-file <file>
  python3 .veris/sandbox/runtime.py --root . collect --instance <id>
  python3 .veris/sandbox/runtime.py --root . destroy --instance <id>

Provision returns a generated instance ID; substitute that exact value.
Use an approved safe command in the argv JSON file.
Never invent an execution result.

Prove:
- Unique per-instance Compose project name
- Required service readiness
- Correct image identity when configured
- Command execution in intended service
- Evidence capture
- Clean teardown of owned containers and volumes
- No conflict when more than one instance is tested

Instance state resides in ignored .veris/runtime-instances/.
Running containers remain on the configured Docker host.
Reusable images remain in the local image store or registry.

Do not treat Docker isolation alone as protection from hostile
untrusted code. Apply additional host and platform controls.

## Phase 7 — Maintain project profile and playbook

Create/update:
- .veris/verification-profile.yaml
- .veris/verification-playbook.md

The profile points to:
  sandbox.configuration_path: .veris/sandbox/sandbox.yaml
  sandbox.adapter_path: .veris/sandbox/runtime.py
  sandbox.provider: docker-compose

Use the actual values discovered and validated. Do not fabricate
image digests or provisioned resources.

The playbook documents:
- Confirmed setup and startup
- Exact public-surface driver instructions
- Independent checker assertions
- Runtime lifecycle commands and clean-state resets
- Secret references and missing identities
- Recovery and cleanup
- Verified and unverified coverage

## Phase 8 — Record checks and compare history

Maintain the v1.1 report contract.

Per run:
- .veris/reports/run-NNNN.md
- .veris/evidence/run-NNNN/results.json

Latest summary:
- .veris/bootstrap-report.md

Baseline required checks:
- environment-start
- surface-flow
- independent-check
- cleanup
- clean-replay

Additional runtime checks when runtime is in scope:
- runtime-definition
- runtime-image-identity
- runtime-start
- runtime-healthcheck
- runtime-command
- runtime-teardown
- runtime-instance-isolation

Mark checks pass/fail/blocked/not_run with evidence.

Compare previous vs current when historical data exists:
  python3 <skill-dir>/scripts/compare_runs.py PREVIOUS CURRENT

Preserve earlier reports, failed attempts, and prior passing checks.
A removed required check is not automatically a safe improvement.

## Phase 9 — Determine readiness

READY:
- Required project checks pass with observed evidence.
- Real user-facing workflow executes and independently passes.
- Clean-state replay and cleanup are demonstrated.
- Required runtime template is validated and ready if in scope.
- No unresolved critical/blocking gaps or baseline regressions.

PARTIAL:
- Some real verification succeeded, but required capabilities or
  reproducibility remain unproven.

BLOCKED:
- Essential verification cannot run because of missing access,
  tools, dependencies, or broken environment.

Mark runtime and project readiness separately where useful.
A sample container starting is not proof that the application
can be verified.

## Phase 10 — Report and handoff

Generate new per-run report and latest report.

Include:
- Mode and run ID
- Project surfaces and technique rationale
- Runtime provider and image identity
- Files produced, actual commands executed
- Environment and representative flow evidence
- Passed/failed/blocked checks
- Changes, resolved gaps, newly discovered gaps
- Baseline comparison and risk
- Approvals needed
- READY/PARTIAL/BLOCKED and justification

Provide downstream instructions:
- Story Verifier and Regression Runner consume the profile,
  sandbox definition and runtime adapter.
- Bootstrap owns hardening the reusable runtime definitions.
- Downstream skills own disposable instances and their cleanup.

Do not perform per-story QA or author regression tests here.
