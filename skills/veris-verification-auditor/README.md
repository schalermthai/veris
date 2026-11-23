# Veris Verification Auditor v1.0

Skill 06 in the Veris verification lifecycle.
Cross-platform: Claude Code and OpenAI Codex.

## Installation

Claude Code:
  .claude/skills/veris-verification-auditor/

Codex:
  .agents/skills/veris-verification-auditor/

## Modes

audit: passive evidence and consistency inspection
benchmark: score independently labeled historical outcomes
incident: trace an escaped production bug through the lifecycle
challenge: explicitly approved experiments in disposable environments

Examples:

Claude:
  /veris-verification-auditor mode=audit

Codex:
  $veris-verification-auditor mode=benchmark

## Requirements

Python 3.9+ standard library.
A project with .veris assets from earlier Veris skills.

The scripts do not depend on a live Docker environment or LLM API.
The coding agent performs semantic judgment and, if authorized,
uses existing tools for controlled challenge experiments.

## Initialize an audit run

From a project root:
  python3 <skill-path>/scripts/collect_evidence.py \
    --root . --mode audit

The command prints the new run path.

## Check consistency

  python3 <skill-path>/scripts/check_consistency.py \
    --root . --run .veris/audits/runs/run-0001

## Evaluate benchmarks

Add independently labeled benchmark JSON files under:
  .veris/audits/benchmarks/

Then:
  python3 <skill-path>/scripts/evaluate_benchmark.py \
    --root . --run .veris/audits/runs/run-0001

The evaluation only scores recorded outcomes. It does not execute
the underlying Story Verifier, Selector, or Runner.

## Finalize the report

Complete audit-report.md and review generated findings and metrics.

Then:
  python3 <skill-path>/scripts/validate_audit.py \
    --root . --run .veris/audits/runs/run-0001 --seal

A successful seal creates audit-seal.json and refreshes
.veris/audits/latest-report.md.

## Compare two audits

  python3 <skill-path>/scripts/compare_audits.py \
    .veris/audits/runs/run-0001 \
    .veris/audits/runs/run-0002

Metrics are comparable only when the labeled benchmark case
identities and file hashes agree.

## Outputs

.veris/audits/
  policy.json
  benchmarks/
  incidents/
  latest-report.md
  runs/
    run-NNNN/
      audit-plan.json
      evidence-index.json
      consistency.json
      benchmark-results.json
      findings.json
      metrics.json
      audit-report.md
      audit-seal.json
      evidence/

Some mode-specific files are optional until the mode is run.

## Security and evidence retention

The evidence index contains source paths and hashes, not raw log
copies. The auditor does not run arbitrary commands found in reports.

Review all reports for secrets and personal data before sharing.
Use a trusted workspace and do not attach sensitive raw artifacts
to tickets without redaction.

An audit is only as good as the independence of its ground truth.

## Testing

From the skill folder:
  python3 -m unittest discover -s tests -v

Tests are offline and use temporary fixture repositories.

## Implementation boundaries

Implemented:
- Passive evidence collection
- Cross-skill record consistency checks
- Labeled historical benchmark scoring
- Findings and metrics validation
- Audit history comparison and sealing

Agent-guided, not automated by generic scripts:
- Semantic assessment of UI evidence
- Historical production incident root cause
- Controlled fault injection in disposable copies
- Applying fixes to other skills

Challenge mode requires explicit authorization and independently
verified induced failures. Never modify production.

This initial package requires runtime validation on a real project
before using audit results as an engineering quality gate.
