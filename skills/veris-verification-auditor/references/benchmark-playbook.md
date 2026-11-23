# Veris Historical Benchmark Playbook

## Purpose

Measure verification quality using independently labeled examples.

Benchmark kinds in this release:
- selection
- story-verdict
- runner-verdict

## Labeling

Each case requires:
- Stable benchmark ID
- Kind
- Independently confirmed ground truth
- Reviewer identity/role description
- Evidence file reference
- Recorded outcome source file
- Expected relevant case IDs or expected verdict

Do not use the verifier's original decision as its own label.

## Selection cases

Expected:
  relevant_case_ids: list of tests that should have been selected.

Optional:
  complete_labels: true
  eligible_case_ids: complete candidate universe.

Recall measures labeled relevant cases selected.

Precision requires full relevance labeling for the eligible universe.
Without complete labels, report precision as unavailable.

An observed selection with missing relevant tests becomes
a benchmark finding, not an automatic product regression.

## Story/Runner verdict cases

expected:
  verdict: failed | verified ... for story
  verdict: failed | passed ... for runner

For known defective cases, detection requires observed failed.
A blocked or inconclusive result is not recorded as successful
defect detection, but it should also be reported separately.

For known clean cases, false rejection means the observed
verdict is a confirmed erroneous FAILED outcome.

## Comparing versions

Use the same cases and labels when comparing skill versions.
Record case file hashes so modifications cannot silently change
the measurement set.

Report changes in:
- Models/versions
- Environment
- Catalog and test definitions
- Observed source revision

These factors may make old and new results non-comparable.

## Avoid leakage

A benchmark run used to evaluate a classifier should not be
secretly rewritten or relabeled based on its classifier output.

Do not use measured recall on a few historical PRs to claim
future generalization performance without qualification.
