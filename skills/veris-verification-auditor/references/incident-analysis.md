# Veris Production Incident Investigation

## Required evidence

Reported user-visible defect and impact.
Affected application surface and environment.
Relevant software version and suspected introducing diff.
Historical verification reports and registered regression cases.
Selector and runner results from the actual release where possible.

## Reconstruct the chain

Requirement
  -> Story Verifier verification plan and actual outcomes
  -> Regression Author preserved E2E behavior
  -> Selector selected/excluded relevant test
  -> Runner actually executed and reported it
  -> Production issue

## Common causal patterns

Missing required acceptance criterion:
  Story requirements or verifier coverage gap.

User action bypassed through internal shortcut:
  Driver/surface fidelity gap.

Weak permanent assertion:
  Regression Author coverage gap.

Relevant existing test excluded:
  Selector impact/policy gap.

Test selected but skipped or falsely green:
  Runner execution/verdict gap.

Correct testing on Chromium, real bug on WebKit:
  Bootstrap/browser coverage and test-authoring gap.

Multiple failures can contribute to a single incident.

## Evidence standards

Use observed artifacts from the time the code was merged.
If historical data is missing, clearly identify uncertainty.
Do not assert one root cause just because it is plausible.

## Remediation

Recommend smallest upstream fix capable of detecting the
same class of failures in future.

Include:
- owning skill
- changed procedure, metadata, rule, or test
- historical repro/benchmark to validate it
- evidence that remediation preserves previous passing behavior

Do not silently change verification assets during incident audit.

## Challenge follow-up

If a labeled case is needed, recreate the problem only in
a disposable approved test environment. Confirm the defect
independently before evaluating verifier detection.
