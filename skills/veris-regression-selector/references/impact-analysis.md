# Veris — Behavioral Impact Analysis

## Core question

Which previously verified user behaviors could the code change break?

## Examine in layers

1. Direct:
   The changed code implements the tested behavior.
2. Shared:
   A service, module, schema, permission rule, or shared dependency
   supports several user journeys.
3. Public contracts:
   Endpoint, event, API payload, CLI flags, or data model changes.
4. Cross-cutting:
   Authentication, sessions, data access, routing, middleware,
   platform or deployment configuration.
5. Unknown:
   Dependency information is insufficient to exclude impact.

## Classes

direct:
  The change is in or directly alters the behavior's implementation.

indirect:
  A shared dependency or downstream consumer is affected.

possible:
  A plausible relationship exists but is not fully established.

unrelated:
  Review provides a concrete explanation for no credible impact.

unknown:
  Unable to determine with enough confidence.

## Selection rule

Include direct, indirect, possible, unknown.
Exclude unrelated only after coding-agent review with a reason.
Never use Jev probabilities alone to justify exclusion.

## Review examples

PermissionService change:
  Ownership, membership, organization access, agent creation may
  be impacted if they call the modified service.

Session storage change:
  Login, resume, logout, and authenticated user journeys may depend
  on it, even when their UI files were unchanged.

Payment implementation change:
  Subscription purchase, upgrade, cancellation, and affected billing
  journeys deserve investigation.

Documentation-only change:
  Some behavior may truly be unrelated, but check for generated
  documentation, shared build scripts, or executable examples.

## Catalog limitations

Metadata may be incomplete or stale. When a test has no components,
do not assume no component dependency exists.

Reasoning must include behavior names, routes, and actual dependency
context where accessible.

Identify uncovered changed behaviors as explicit coverage gaps.
