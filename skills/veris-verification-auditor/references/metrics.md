# Veris Audit Metrics Contract

## Requirements

Report numerator, denominator, value, scope, and limitations.
Null value when denominator is zero.

Do not calculate outcome accuracy from unlabeled prior verdicts.

## Selection recall

Numerator:
  Independently labeled relevant test/PR relationships selected.
Denominator:
  All independently labeled relevant relationships evaluated.

selection_recall = relevant_selected / relevant_labeled

## Selection precision

Requires complete relevance labels for the eligible universe.

Numerator:
  Selected cases labeled relevant.
Denominator:
  All selected cases in the fully labeled universe.

Do not compute from positive-only labels.

## Known-defect detection recall

Numerator:
  Known defective verification cases reported FAILED.
Denominator:
  All evaluated known defective labeled cases.

A blocked/inconclusive outcome does not count as detected.
Report such outcomes in details for diagnostic interpretation.

## False rejection rate

Numerator:
  Independently labeled clean cases reported FAILED.
Denominator:
  Evaluated independently labeled clean cases.

Blocked/inconclusive outcomes are not false rejection but
indicate incomplete evaluation and should be reported separately.

## Other useful audit data

- Evidence completeness rate
- Cleanup success rate
- Confirmed flakiness rate
- False green verdict count
- Unresolved mandatory case count
- Auditability and artifact drift counts

These are separate from labeled detection metrics.

## Interpretation

A benchmark with 9/10 recalls only establishes 90% on those
ten labeled examples, not on every future change.

Preserve benchmark IDs and hashes for comparisons.
If the sample changed, describe results separately.
