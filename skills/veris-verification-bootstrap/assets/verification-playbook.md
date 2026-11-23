# Veris Project Verification Playbook

## Application
Project:
Architecture:
Primary user-facing surface:
Other surfaces:
Runtime and services:

## Principles
- Driver uses real user-facing interface.
- Setup may use approved fixture shortcuts.
- Checker independently confirms relevant outcomes.
- Evidence must be real and reproducible.
- No production credentials or uncontrolled side effects.

## Setup
Prerequisite dependencies:
Required environment variable NAMES:
Secret injection mechanism:
Test identities and accounts:
Confirmed setup command:
Confirmed readiness condition:
Test fixture creation:
State reset:

## Driver
Surface:
Tool:
User journey:
Allowed actions:
Prohibited internal shortcuts:
Expected visible result:

## Checker
Independent oracles:
State checks:
Permissions and side effects:
Unexpected UI/behavior checks:
Evidence:

## Shared runtime
Provider:
Contract path: .veris/sandbox/sandbox.yaml
Adapter path: .veris/sandbox/runtime.py
Compose path:
Image reference:
Image local ID or registry digest:
Template status:
Required services:
Exec service:
Isolation and cleanup:

Validated lifecycle:
1. provision
2. start
3. healthcheck
4. execute approved command
5. collect evidence
6. destroy

Last validated runtime run:
Limitations and required approvals:

## Representative E2E
Initial state:
Real-surface actions:
Independent checks:
Observed result:
Clean-state replay result:
Evidence:

## Troubleshooting
Known failure:
Diagnostic:
Recovery:
Recheck:

## Maintenance
Update when startup, dependencies, integrations, browsers,
fixtures, image identities, or provider requirements change.

## Handoff
Story Verifier uses this environment for ad hoc QA.
Regression Runner uses it for selected E2E cases.
Bootstrap owns reusable image and runtime definition.
